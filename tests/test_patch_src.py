"""字块换底图：`?src=bin|color|auto`（彩图书双层显示，2026-11-18）。同一个 bbox_page 在二值副本与原图上裁到同一处。"""
import json

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

import guji_manager.console_api as CA
from guji_console.routers import products as P


@pytest.fixture
def page(tmp_path, monkeypatch):
    W, H = 200, 120
    color = np.zeros((H, W, 3), np.uint8)
    color[:] = (170, 215, 230)
    color[30:60, 120:160] = (40, 40, 200)                      # 朱印（左上原点 x 120..160）
    raw = tmp_path / "raw.png"
    cv2.imwrite(str(raw), color)
    binp = tmp_path / "1.png"
    cv2.imwrite(str(binp), np.full((H, W), 255, np.uint8))
    binp.with_suffix(".qc.json").write_text(json.dumps(
        {"page": 1, "size": [W, H], "regions": [{"bbox": [120, 30, 160, 60], "reason": "color_mark", "score": 0.5}]}))
    monkeypatch.setattr(CA, "binarized_or_none", lambda book, p: binp, raising=False)
    monkeypatch.setattr(CA, "effective_raw_path", lambda b, p: raw, raising=False)
    monkeypatch.setattr(P, "load_book", lambda book: object())
    return W


def _box_canon(W, x0, y0, x1, y1):
    return [(W - 1) - x1, y0, (W - 1) - x0, y1]


def _decode(resp):
    return cv2.imdecode(np.frombuffer(resp.body, np.uint8), cv2.IMREAD_UNCHANGED)


def test_color_and_bin_same_box(page, monkeypatch):
    W = page
    monkeypatch.setattr(P, "_char_box", lambda book, key: (1, _box_canon(W, 120, 30, 160, 60)))
    c = P._char_patch_recrop("tb", "p0001c01s1", "color")
    b = P._char_patch_recrop("tb", "p0001c01s1", "bin")
    assert c.headers["X-Img-Src"] == "color" and b.headers["X-Img-Src"] == "bin"
    ci, bi = _decode(c), _decode(b)
    assert ci.shape[:2] == bi.shape[:2] == (30, 40)
    assert (ci[:, :, 2] == 200).all()                          # 裁到的是朱印，不是镜像那边的纸


def test_auto_picks_color_only_in_suspect(page, monkeypatch):
    W = page
    monkeypatch.setattr(P, "_char_box", lambda book, key: (1, _box_canon(W, 120, 30, 160, 60)))
    assert P._char_patch_recrop("tb", "k", "auto").headers["X-Img-Src"] == "color"
    monkeypatch.setattr(P, "_char_box", lambda book, key: (1, _box_canon(W, 10, 70, 40, 100)))
    assert P._char_patch_recrop("tb", "k", "auto").headers["X-Img-Src"] == "bin"


def test_missing_box_returns_none(page, monkeypatch):
    monkeypatch.setattr(P, "_char_box", lambda book, key: None)
    assert P._char_patch_recrop("tb", "k", "color") is None
