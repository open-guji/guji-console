# -*- coding: utf-8 -*-
"""cards 结果缓存 + 按格 embedding 缓存 + 原型按例增量（overview #166 加急，2026-09-28）。

服务器上全唐文开 CNN 首选后 `/api/review/cards` >180 s、RSS 3.27G：原型缓存键含库内容
指纹，本书库每进一例刻例就整库重跑 CNN；每次请求又给全书待审格重算 embedding。
"""
from __future__ import annotations

import numpy as np
import pytest


def _u(*v) -> np.ndarray:
    a = np.asarray(v, np.float32)
    return a / np.linalg.norm(a)


# ── cards 结果缓存 ──────────────────────────────────────────────────

@pytest.fixture
def cache_env(ws, tmp_path, monkeypatch):
    from open_guji_cv.review import cards as C
    fb = tmp_path / "fb"
    (fb / "events").mkdir(parents=True)
    monkeypatch.setenv("GUJI_FEEDBACK_DIR", str(fb))
    monkeypatch.setenv("GUJI_CACHE_DIR", str(tmp_path / "cache"))
    C.clear_cards_cache()
    yield fb
    C.clear_cards_cache()


# ── 路由：缓存头、响应体与直接装配逐字节一致 ────────────────────────────────

def test_route_cards_cache_header_and_identical_body(cache_env, monkeypatch):
    import importlib

    from fastapi.testclient import TestClient
    app = importlib.import_module("guji_console.app").app
    console_auth = importlib.import_module("guji_console.auth")
    Identity = importlib.import_module("guji_console.auth.identity").Identity
    app.dependency_overrides[console_auth.get_identity] = lambda: Identity(
        email="r@example.com", role="reviewer", tier="reviewer")
    try:
        c = TestClient(app)
        q = "/api/review/cards?book=keben&pages=1&group=char&gate_cut=false"
        r1, r2 = c.get(q), c.get(q)
        assert r1.status_code == 200, r1.text
        assert r1.headers["X-Cards-Cache"] == "miss" and r2.headers["X-Cards-Cache"] == "mem"
        assert r1.content == r2.content
        r3 = c.get("/api/review/cards?book=keben&pages=1&gate_cut=false")
        assert r3.status_code == 200 and r3.json()["cards"] == []
    finally:
        app.dependency_overrides.clear()


# ── 按格 embedding 缓存（`borrow_first.EmbCache`）─────────────────────────

class _ManStore:
    def __init__(self, sha):
        self.sha = sha

    def manifest(self, book, step):
        sha = self.sha

        class _M:
            def get(self, key):
                return type("E", (), {"sha256": sha})()
        return _M()


# ── 原型增量重建（#166 加急：库一变不再整库重跑 CNN）───────────────────────

def _mini_db(path, items):
    import sqlite3

    c = sqlite3.connect(path)
    c.executescript("""
      CREATE TABLE glyphs (glyph_id INTEGER PRIMARY KEY, char TEXT, updated_at TEXT);
      CREATE TABLE exemplars (glyph_id INTEGER, instance_id TEXT, role TEXT, added_at TEXT,
                              PRIMARY KEY (glyph_id, instance_id));
      CREATE TABLE admissions (admitted_at TEXT);
      CREATE TABLE derived (instance_id TEXT, kind TEXT, algo_version TEXT, data BLOB,
                            PRIMARY KEY (instance_id, kind, algo_version));""")
    _mini_add(c, items)
    return c


def _mini_add(c, items):
    import cv2
    for ch, iid, v in items:
        gid = c.execute("SELECT glyph_id FROM glyphs WHERE char=?", (ch,)).fetchone()
        if gid is None:
            gid = (c.execute("INSERT INTO glyphs (char, updated_at) VALUES (?, 't')", (ch,)).lastrowid,)
        img = np.full((64, 64), v, np.uint8)
        c.execute("INSERT INTO exemplars VALUES (?,?,'x',?)", (gid[0], iid, iid))
        c.execute("INSERT INTO derived VALUES (?, 'norm', 'v1', ?)",
                  (iid, cv2.imencode(".png", img)[1].tobytes()))
    c.commit()


class _CountingCnn:
    from pathlib import Path as _P
    ckpt = _P("/nonexistent/best.pt")

    def __init__(self):
        self.n = 0

    def embed(self, imgs):
        self.n += len(imgs)
        return np.stack([_u(float(im.mean()) + 1.0, 1.0) for im in imgs])


