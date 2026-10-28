# -*- coding: utf-8 -*-
"""待审卡按 doubt 码筛选（overview#215）：`cards(doubt=…)` 与 `/api/review/cards?doubt=…`。

产物自己造（`PageAdmit` 直接构造），不扫真书。三条要守的：
不传 `doubt` 时响应与改前逐字节一致；计数不受 `limit` 截断；缓存键带上新参数。
"""
from __future__ import annotations

import importlib
import json

import pytest

import open_guji_cv.steps  # noqa: F401  注册产物种类


def _rec(cid, slot, doubts, *, admit=False, char="之", evidence=None):
    from open_guji_cv.products.kinds.recog import AdmitRec
    return AdmitRec(id=cid, slot=slot, admit=admit, char=char, doubts=doubts,
                    evidence=evidence or {})


@pytest.fixture
def env(ws, tmp_path, monkeypatch):
    """keben 两页待审卡：各种 doubt 码组合 + 一张自动档 + 一张排除名单。"""
    from open_guji_cv.core.spec import page_key
    from open_guji_cv.products.kinds.recog import ColumnAdmit, PageAdmit
    from open_guji_cv.products.store import ProductStore
    from open_guji_cv.review import cards as C
    fb = tmp_path / "fb"
    (fb / "events").mkdir(parents=True)
    monkeypatch.setenv("GUJI_FEEDBACK_DIR", str(fb))
    monkeypatch.setenv("GUJI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("GUJI_PRODUCTS_DIR", str(tmp_path / "products"))
    st = ProductStore(tmp_path / "products")
    occ = {"occluded": {"via": "coord", "ref_blank": False}}
    p1 = [
        _rec("keben:1:1:1", 1, ["occluded"], char="天", evidence=occ),
        _rec("keben:1:1:2", 2, ["channel_off", "库里没有这个字"]),
        _rec("keben:1:1:3", 3, ["replace_form"]),
        _rec("keben:1:1:4", 4, ["库 unsure(cov=0.123)"]),        # 只有中文说明 → _none
        _rec("keben:1:1:5", 5, [], admit=True),                   # 自动档，only=review 不出
        _rec("keben:1:1:6", 6, ["excluded"]),                     # 排除名单，不出也不计
    ]
    p2 = [
        _rec("keben:2:1:1", 1, ["channel_off", "variant_indirect"]),
        _rec("keben:2:1:2", 2, ["occluded"], char=None,
             evidence={"occluded": {"via": "coord", "ref_blank": True}}),
        _rec("keben:2:1:3", 3, ["solo_confusable"]),
    ]
    for pg, recs in ((1, p1), (2, p2)):
        st.write("keben", "seed_admit", page_key(pg),
                 {"seed_admit": PageAdmit(page=pg, columns=[ColumnAdmit(col=1, chars=recs)])})
    C.clear_cards_cache()
    yield st
    C.clear_cards_cache()


def _ids(res):
    return [c["id"] for c in res["cards"]]


# ── 语法 ────────────────────────────────────────────────────────────


# ── cards() ─────────────────────────────────────────────────────────


# ── 路由 ────────────────────────────────────────────────────────────

@pytest.fixture
def client(env):
    from fastapi.testclient import TestClient
    app = importlib.import_module("guji_console.app").app
    console_auth = importlib.import_module("guji_console.auth")
    Identity = importlib.import_module("guji_console.auth.identity").Identity
    app.dependency_overrides[console_auth.get_identity] = lambda: Identity(
        email="r@example.com", role="reviewer", tier="reviewer")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_route_no_param_byte_identical(client, env):
    """不传 doubt 的响应体 = 直接调 `cards()`（改前的装配）序列化出来的那份。"""
    from open_guji_cv.review.cards import cards
    r = client.get("/api/review/cards?book=keben&pages=1-2&gate_cut=false&skip_decided=false")
    assert r.status_code == 200, r.text
    want = cards("keben", "1-2", 400, "review", env, gate_cut=False, skip_decided=False)
    assert r.json() == json.loads(json.dumps(want, ensure_ascii=False))
    assert "doubt_counts" not in r.json()


def test_route_filter_counts_and_cache_key(client):
    q = "/api/review/cards?book=keben&pages=1-2&gate_cut=false&skip_decided=false"
    r0 = client.get(q)
    r1 = client.get(q + "&doubt=occluded")
    r2 = client.get(q + "&doubt=occluded")
    r3 = client.get(q + "&doubt=channel_off")
    assert r1.status_code == 200, r1.text
    # 新参数进了缓存键：头一回带 doubt 是 miss，不会读回不带 doubt 的那份
    assert r0.headers["X-Cards-Cache"] == "miss" and r1.headers["X-Cards-Cache"] == "miss"
    assert r2.headers["X-Cards-Cache"] == "mem" and r3.headers["X-Cards-Cache"] == "miss"
    assert [c["id"] for c in r1.json()["cards"]] == ["keben:1:1:1", "keben:2:1:2"]
    assert [c["id"] for c in r3.json()["cards"]] == ["keben:1:1:2", "keben:2:1:1"]
    assert r1.json()["doubt_counts"]["occluded"] == 2
    assert client.get(q + "&doubt=坏码").status_code == 400


def test_route_grouped_modes_carry_counts(client):
    q = "/api/review/cards?book=keben&pages=1-2&gate_cut=false&skip_decided=false&group=char"
    r = client.get(q + "&doubt=channel_off")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["n_total"] == 2 and d["doubt_counts"]["channel_off"] == 2
    assert "doubt_counts" not in client.get(q).json()
