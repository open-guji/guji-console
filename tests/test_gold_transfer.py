"""裁决表 ⇄ 测试集的两个显式动作（gold/transfer.py）+ 三仓边界的运行时默认。

2026-09-13 用户裁定：管线运行时只读写 workspace；人裁先落 workspace 裁决表
（feedback/verdicts/），只有显式 `guji gold import` 才进 open-guji-dataset。
"""

from __future__ import annotations

import pytest

from open_guji_cv.gold.item import Anchor, GoldItem
from open_guji_cv.gold.store import GoldStore

SHARD = "char-segmentation/touching-cuts"


def _item(page, col, slot, book="vol02", status="active", stratum=None, **expected):
    return GoldItem(id=f"{book}:{page}:{col}:{slot}",
                    anchor=Anchor(book=book, page=page, col=col, slot=slot),
                    expected=expected or {"verdict": "ok"}, status=status, stratum=stratum)


@pytest.fixture
def stores(tmp_path):
    src = GoldStore(tmp_path / "ws" / "feedback" / "verdicts")
    dst = GoldStore(tmp_path / "dataset")
    return src, dst


def test_console_verdict_store_follows_feedback_root(monkeypatch, tmp_path):
    from guji_console import deps
    deps.set_roots(feedback=tmp_path / "fb", dataset=tmp_path / "ds")
    try:
        assert deps.verdict_store().root == tmp_path / "fb" / "verdicts"
        assert deps.gold_store().root == tmp_path / "ds"
    finally:
        deps.set_roots()
        deps._roots.update({"feedback": None, "dataset": None})
        deps._log = deps._batches = deps._gold = deps._verdicts = None
