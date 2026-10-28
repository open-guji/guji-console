# -*- coding: utf-8 -*-
"""近似字（overview#276）：人裁卡「无匹配（近似字）」→ 事件 → 侧表 `approx_labels` → 导出/同步 → 闸与文本。

钉住：
1. 老事件（不带 approx）行为完全不变：读回形状、进库结果、库内容、指纹、seed_admit 参数哈希；
2. 带 approx 的 confirm 写侧表（ids/note/reviewer 可空），人改口撤掉并记 `approx_clears`，撤例跟着删；
3. 库指纹（`db_fingerprint`）空表不变、有行也不变（建议见 HANDOFF_H276）；
4. 查询「某字有没有近似例」与字表角标计数；
5. seed_admit：匹配到近似例缺省照常放行、evidence 标注（用户 09-29 裁定 #277 选 C）；开闸则落人审；
6. 文本：缺省正文照填 + 侧表（来源 人裁/匹配），`inline_ids` 选项括注；
7. 前端 `verdictRow`（node 跑 reviewClass.ts）。
导出签名见 `ops.central_glyph.export_signature`（中心库 push／sync 前据此决定要不要先导出）。
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

import open_guji_cv.steps  # noqa: F401
from open_guji_cv.clustering.glyph_db import GlyphDB
from open_guji_cv.feedback.events import EventTarget, make_event

BOOK = "abook"


def _png(k: int = 0) -> bytes:
    img = np.full((80, 80), 255, np.uint8)
    cv2.rectangle(img, (6 + k % 20, 10), (70, 70 - k % 15), 0, 4)
    cv2.line(img, (10, 10 + k % 30), (70, 40), 0, 3)
    return cv2.imencode(".png", img)[1].tobytes()


def _ev(key: str, payload: dict, seq: int = 1, ts: str | None = None, actor: str = "user",
        reviewer: str | None = None, batch: str = "b"):
    _b, pg, col, slot = key.split(":")
    return make_event(batch, seq, "confirm",
                      EventTarget(step="seed_admit", unit="cell", key=key, book=_b,
                                  page=int(pg), col=int(col), slot=int(slot)),
                      payload, actor=actor, ts=ts, reviewer=reviewer)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """空库里已有一格人裁（`v2:abook:1:1:1` 定「之」）：消费者走「缓存里没有 → 用库里那张」的路，
    不必现跑 Step1→Step4。"""
    monkeypatch.setenv("GUJI_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "g.db"
    g = GlyphDB(p)
    assert g.admit_instance(f"v2:{BOOK}:1:1:1", "之", _png(1), provenance="human",
                            page="1", col=1, idx=1)
    g.conn.commit()
    g.close()
    return p


def _dump(p: Path) -> dict:
    c = sqlite3.connect(p)
    try:
        out = {}
        for t in ("instances", "admissions", "exemplars", "glyphs", "evictions",
                  "approx_labels", "approx_clears"):
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
            keep = [x for x in cols if x not in ("patch_png", "updated_at", "admitted_at",
                                                 "added_at", "at")]
            out[t] = sorted(c.execute(f"SELECT {','.join(keep)} FROM {t}").fetchall(), key=repr)
        return out
    finally:
        c.close()


# ── 1. 读回 ──────────────────────────────────────────────────────────────


# ── 2. 进库 ──────────────────────────────────────────────────────────────


# ── 3. 指纹 ──────────────────────────────────────────────────────────────


# ── 4. 查询 ──────────────────────────────────────────────────────────────


# ── 5. seed_admit 闸 ─────────────────────────────────────────────────────


def _run_seed(tmp_path, monkeypatch, db_path, recs, **params):
    from helpers import make_book, make_ctx, page_decision, write_product
    from open_guji_cv.core.step import STEPS, RunContext
    from open_guji_cv.products.kinds.cells import CellRec, ColumnCells, PageCells
    from open_guji_cv.products.kinds.recog import ColumnMatch, PageAlignRef, PageMatch
    from open_guji_cv.steps.seed_admit import SeedAdmitParams
    monkeypatch.setenv("GUJI_FEEDBACK_DIR", str(tmp_path / "fb"))
    img = np.full((600, 600), 255, np.uint8)
    ctx = make_ctx(tmp_path, make_book("tbook"), raw={1: img}, monkeypatch=monkeypatch)
    ctx = RunContext(ctx.book, ctx.store, ctx.cache,
                     params={"seed_admit": SeedAdmitParams(db_path=str(db_path), **params)},
                     log=lambda s: None)
    ctx._raw[1] = img
    cells = [CellRec(slot=s, pos=s, y0=0, y1=10, x0=0, x1=10, kind="char", order=s) for s in (1, 2, 3)]
    write_product(ctx, "glyph_match", 1,
                  glyph_match=PageMatch(page=1, columns=[ColumnMatch(col=3, ok=True, chars=recs)]))
    write_product(ctx, "context_decide", 1, context_decision=page_decision(1, "tbook", recs=[], col=3))
    write_product(ctx, "row_segment", 1,
                  cells=PageCells(page=1, period=10.0, ref_w=10.0,
                                  columns=[ColumnCells(col=3, ok=True, n_body_slots=3, period=10.0,
                                                       border_top=0.0, cells=cells)]))
    write_product(ctx, "align_ref", 1, align_ref=PageAlignRef(page=1, anchored=False, coord=[]))
    sa = STEPS["seed_admit"].run_page(ctx, 1)["seed_admit"]
    return {r.slot: r for cc in sa.columns for r in cc.chars}


# ── 6. 文本 ──────────────────────────────────────────────────────────────


# ── 7. 前端事件行 ─────────────────────────────────────────────────────────

TS = (Path(__file__).resolve().parents[1]
      / "guji_console/frontend/src/components/review/reviewClass.ts")


def _node_ok() -> bool:
    node = shutil.which("node")
    return bool(node) and subprocess.run([node, "--experimental-strip-types", "-e", "0"],
                                         capture_output=True).returncode == 0


@pytest.mark.skipif(not _node_ok(), reason="没有支持 --experimental-strip-types 的 node（≥22.6）")
def test_ts_verdict_row_approx(tmp_path):
    shutil.copy(TS, tmp_path / "reviewClass.mts")
    runner = tmp_path / "run.mts"
    runner.write_text("""import * as R from './reviewClass.mts'
const base = { shape: '乃', done: '1', ts: 1, dwell: 2 }
const prev = { ...base, approx: true, approxIds: '⿱丿乃', approxNote: '' }
console.log(JSON.stringify({
  old: R.verdictRow('a', base),
  off: R.verdictRow('a', { ...base, approx: false, approxIds: 'x' }),
  on: R.verdictRow('a', prev),
  kept: R.pickVerdict('及', prev, 0, 5),
  seg: R.verdictRow('a', { ...prev, done: 'truncated' }),
}))
""", encoding="utf-8")
    out = json.loads(subprocess.run([shutil.which("node"), "--experimental-strip-types", "--no-warnings",
                                     str(runner)], capture_output=True, text=True, check=True).stdout)
    assert out["old"] == {"id": "a", "v": "confirm", "shape": "乃", "no_glyph_lib": False,
                          "client_ts": 1, "dwell_ms": 2}, "不勾近似：事件逐字段与原来相同"
    assert out["off"] == out["old"]
    assert out["on"] == {**out["old"], "approx": True, "ids": "⿱丿乃"}, "note 空串不写"
    assert out["kept"]["approx"] is True and out["kept"]["shape"] == "及", "改字不丢勾选"
    assert "approx" not in out["seg"], "近似只随定字（v=confirm）走"


pytestmark = pytest.mark.usefixtures("seed_admit_switches_off")   # 老测试按「放行开关缺省全关」造的数据，见 conftest
