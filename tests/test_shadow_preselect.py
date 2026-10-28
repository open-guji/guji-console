# -*- coding: utf-8 -*-
"""影子预勾（overview#269）：对齐改字层网格用影子排序＋预勾。数据自己造。

守的：
1. 没有预测文件：卡片与改前一致（无 `shadow` 字段），`shadow_info.available=false`，不报错；坏文件同。
2. 有预测文件、网格：把握≥0.9 且影子字==整理本字的卡（`pre`）排最前（按把握降序），其余保持原序，
   排序发生在 `limit` 截断之前；`shadow=False` 关掉后回到原序、无 `shadow` 字段。
3. 路由：`shadow=false` 与文件指纹进缓存键（换文件／开关都不串）。
4. 事件行（node 跑 reviewClass.ts）：给 `shadowOn` 才带 `shadow_preselect`，不给与改前逐字节一致；
   预勾被点掉的行 v≠confirm 而 shadow_preselect=true。
5. 导出脚本：`shadow_picks.jsonl` → 文件格式。
"""
from __future__ import annotations

import json


from test_replace_align_grid import (RA, _rec, _run_ts, client, env, needs_node)  # noqa: F401  复用夹具


def _write_shadow(tmp_path, cells, book="keben"):
    from open_guji_cv.review.shadow import shadow_path
    p = shadow_path(book)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": 1, "book": book, "cells": cells}, ensure_ascii=False),
                 encoding="utf-8")
    return p


KW = dict(gate_cut=False, skip_decided=False)


def test_route_shadow_cache_key(client, tmp_path):
    q = ("/api/review/cards?book=keben&pages=1&gate_cut=false&skip_decided=false"
         "&cls=replace_align&cls_sub=grid")
    a = client.get(q).json()
    assert a["shadow_info"]["available"] is False
    _write_shadow(tmp_path, {"keben:1:1:4": {"char": "地", "conf": 0.95}})
    b = client.get(q).json()                             # 文件出现 → 指纹进键，不吃旧缓存
    assert [c["id"] for c in b["cards"]] == ["keben:1:1:4", "keben:1:1:3"]
    off = client.get(q + "&shadow=false").json()          # 关掉 → 另一个键
    assert [c["id"] for c in off["cards"]] == ["keben:1:1:3", "keben:1:1:4"]
    assert "shadow" not in off["cards"][0]


@needs_node
def test_ts_grid_rows_shadow_preselect_field(tmp_path):
    out = _run_ts(tmp_path, """
const cards = [{ id: 'a', ref: { char: '天' }, shadow: { pre: true } },
               { id: 'b', ref: { char: '地' }, shadow: { pre: false } },
               { id: 'c', ref: { char: '玄' } }]
const states = { a: 'review' }                   // 预勾的被人点成要细审
const plain = R.gridRows(cards, states, 1, 2)
const on = R.gridRows(cards, states, 1, 2, undefined, true)
const off = R.gridRows(cards, states, 1, 2, undefined, false)
const flag = R.gridFlagRows(cards, states, 2, true)
console.log(JSON.stringify({ plain, on, off, flag, n: R.countShadowPre(cards) }))
""")
    assert all("shadow_preselect" not in r for r in out["plain"])           # 旧调用逐字节不变
    strip = lambda rows: [{k: v for k, v in r.items() if k != "shadow_preselect"} for r in rows]
    assert strip(out["on"]) == out["plain"] == strip(out["off"])
    assert [(r["id"], r["v"], r["shadow_preselect"]) for r in out["on"]] == \
        [("b", "confirm", False), ("c", "confirm", False)]            # a 要细审：不写 confirm
    assert all(r["shadow_preselect"] is False for r in out["off"])
    assert out["flag"] == [{"id": "a", "via": "grid", "client_ts": 2, "shadow_preselect": True}]
    assert out["n"] == 1


