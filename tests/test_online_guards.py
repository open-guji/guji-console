# -*- coding: utf-8 -*-
"""上线（console.kaiyuanguji.com）前的几道护栏（第二步 W1，Sheldon 10-29）。

- 每条路由都要有鉴权级别，只有下面 `PUBLIC` 里列的几条可以免登录——新加路由忘了挂
  `require_reviewer`／`require_admin` 这里就红；
- `GUJI_CONSOLE_MIN_TIER=admin`：第一阶段只开给网站管理员，校对者登录后 403；
- `GUJI_CONSOLE_NO_RUNS=1`：线上服务器不跑管线，下单一律 403。
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

#: 免登录的路由：健康检查、版本、登录流程本身、前端外壳（外壳里的数据都走 /api/*，各自要登录）。
PUBLIC = {
    ("GET", "/healthz"), ("GET", "/api/version"),
    ("GET", "/auth/login"), ("GET", "/auth/callback"), ("GET", "/auth/logout"),
    ("GET", "/auth/dev-login"), ("GET", "/auth/dev-login-submit"),
    ("GET", "/"), ("GET", "/v1/"), ("GET", "/{full_path:path}"),
}


@pytest.fixture(autouse=True)
def _fresh():
    global app_mod, auth_config, guard, session
    app_mod = importlib.import_module("guji_console.app")
    auth_config = importlib.import_module("guji_console.auth.config")
    guard = importlib.import_module("guji_console.auth.guard")
    session = importlib.import_module("guji_console.auth.session")
    auth_config.reset_config()
    auth_config.set_config(session_secret="test-session-secret")
    yield
    auth_config.reset_config()


def _deps(dependant) -> set:
    out = set()
    for d in dependant.dependencies:
        out.add(d.call)
        out |= _deps(d)
    return out


def test_every_route_has_an_auth_level():
    levels = {guard.get_identity, guard.require_reviewer, guard.require_admin}
    bare = []
    for mod in app_mod.ROUTERS:
        router_deps = {d.dependency for d in mod.router.dependencies}
        for r in mod.router.routes:
            if not isinstance(r, APIRoute):
                continue
            if (_deps(r.dependant) | router_deps) & levels:
                continue
            bare += [(m, r.path) for m in r.methods if (m, r.path) not in PUBLIC]
    assert bare == [], f"这些路由没挂鉴权级别：{bare}"


def _cookie(tier: str) -> dict:
    cfg = auth_config.get()
    token = session.build_session_token(email=f"{tier}@example.com", role=tier, tier=tier,
                                        ttl=cfg.session_ttl, secret=cfg.session_secret)
    return {session.SESSION_COOKIE: token}


def test_min_tier_admin_shuts_out_reviewers():
    client = TestClient(app_mod.app, follow_redirects=False)
    assert client.get("/api/books", cookies=_cookie("reviewer")).status_code == 200
    auth_config.set_config(min_tier="admin")
    assert client.get("/api/books", cookies=_cookie("reviewer")).status_code == 403
    assert client.get("/api/books", cookies=_cookie("admin")).status_code == 200
    assert client.get("/healthz").status_code == 200


def test_min_tier_and_no_runs_read_from_env(monkeypatch):
    monkeypatch.setenv("GUJI_CONSOLE_MIN_TIER", "admin")
    monkeypatch.setenv("GUJI_CONSOLE_NO_RUNS", "1")
    auth_config.reset_config()
    cfg = auth_config.get()
    assert cfg.min_tier == "admin" and cfg.no_runs is True


def test_no_runs_refuses_to_queue_pipelines():
    auth_config.set_config(no_runs=True)
    client = TestClient(app_mod.app, follow_redirects=False)
    r = client.post("/api/runs", json={"book": "vol01"}, cookies=_cookie("admin"))
    assert r.status_code == 403 and "不跑管线" in r.json()["detail"]
