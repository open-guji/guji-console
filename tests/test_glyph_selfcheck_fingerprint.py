# -*- coding: utf-8 -*-
"""体检结果带库指纹，过期不出卡（GUJI-710）。

起因（GUJI-623）：findings.jsonl 是 09-26 的库算的，09-27 刻例重排编号后没重跑，控制台照样出卡，
实例 id 已指向别的图，9 张卡错位。这里自造一个小库，不跑真体检（HOG＋弹性验证太慢），
直接造 `run_selfcheck` 形状的结果走 `save` → `freshness` → 控制台路由。"""

from __future__ import annotations

import json
import sqlite3

import cv2
import numpy as np
import pytest

from open_guji_cv.clustering import glyph_selfcheck as G
from open_guji_cv.clustering.glyph_db import GlyphDB


def _png(k):
    img = np.full((64, 64), 255, np.uint8)
    cv2.rectangle(img, (10 + k, 10), (50, 50 - k), 0, 3)
    return cv2.imencode(".png", img)[1].tobytes()


@pytest.fixture()
def lib(tmp_path):
    p = tmp_path / "output" / "glyph.db"
    p.parent.mkdir()
    g = GlyphDB(p)
    g.admit_instance("bk:1:1:1", "王", _png(0), provenance="align", page="1", col=1, idx=1)
    g.admit_instance("bk:1:1:2", "王", _png(1), provenance="align", page="1", col=1, idx=2)
    g.admit_instance("bk:1:1:3", "干", _png(2), provenance="human", page="1", col=1, idx=3)
    g.admit_instance("bk:1:1:4", "土", _png(3), provenance="align", page="1", col=1, idx=4)
    g.close()
    return p


def _result(db):
    """`run_selfcheck` 形状的结果：两张卡（1 形似 3「干」；4 同字离群、参照 2）。"""
    rows = G.library_rows(db)
    f1 = G.Finding("bk:1:1:1", "王", "align", flags=["rival"], rival=0.95, rival_char="干",
                   rival_peer="bk:1:1:3", rival_prov="human", same_peer="bk:1:1:2")
    f2 = G.Finding("bk:1:1:4", "土", "align", flags=["outlier"], n_same_self=1,
                   best_same_self=0.5, same_peer="bk:1:1:2")
    refs = {i for f in (f1, f2) for i in G._card_refs(G.asdict(f))}
    return {"db": str(db), "db_fp": G._fingerprint(rows),
            "inst_sha": {i: rows[i][1] for i in refs}, "n_checked": 4, "n_flagged": 2,
            "findings": [f1, f2], "all": [f1, f2]}


def _swap_image(db, iid, k):
    c = sqlite3.connect(db)
    c.execute("UPDATE instances SET patch_png=? WHERE instance_id=?", (_png(k), iid))
    c.commit()
    c.close()


def test_console_route_refuses_stale(lib, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi import HTTPException

    from guji_console.routers.glyphlib import api_glyphlib_audit
    monkeypatch.setenv("GUJI_GLYPH_DB", str(lib))
    out = G.save(_result(lib), G.out_dir())
    assert out == lib.parent / "glyph_selfcheck"
    got = api_glyphlib_audit()
    assert got["n_total"] == 2 and len(got["findings"]) == 2
    assert got["db_fp"] == G.library_fingerprint(lib)

    _swap_image(lib, "bk:1:1:1", 8)
    with pytest.raises(HTTPException) as ei:
        api_glyphlib_audit()
    assert ei.value.status_code == 409
    assert G.STALE_MSG in ei.value.detail

    # 旧结果（没有 db_fp）同样不出卡
    _swap_image(lib, "bk:1:1:1", 0)
    meta = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    meta.pop("db_fp")
    (out / "summary.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(HTTPException) as ei:
        api_glyphlib_audit()
    assert ei.value.status_code == 409
