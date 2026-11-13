# -*- coding: utf-8 -*-
"""前端 pendingReasons.ts 是 guji-manager `pending_reasons.yaml` 的导出副本；真源加了码这里没重新导出，
控制台就把新码显示成「原因不明」（A01–A03 在网站漏过一次，kaiyuanguji-web#765）。这里核对码、名称、去向与真源一致。
重新导出：`python -m guji_manager.review.pending_reason --json > pr.json`，再用 kaiyuanguji-web 的
`ops/gen_pending_reasons_ts.py pr.json guji_console/frontend/src/pendingReasons.ts`，然后重新 build 前端。"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TS = Path(__file__).resolve().parents[1] / "guji_console" / "frontend" / "src" / "pendingReasons.ts"


def _ts_reasons() -> dict[str, dict]:
    """从 TS 里取 PENDING_REASONS 块：键 → {code, label}（生成脚本每项固定缩进 4 格）。"""
    text = TS.read_text(encoding="utf-8")
    block = text.split("export const PENDING_REASONS = {", 1)[1].split("} as const;", 1)[0]
    out = {}
    for m in re.finditer(r'^    ("[a-z_]+"): \{\n(.*?)^    \}', block, re.S | re.M):
        key = json.loads(m.group(1))
        body = json.loads("{" + m.group(2).strip().rstrip(",") + "}")
        out[key] = body
    return out


def test_ts_copy_matches_manager():
    pr = pytest.importorskip("guji_manager.review.pending_reason")
    src = pr.export()["reasons"]
    ts = _ts_reasons()
    assert ts, "没解析出任何原因，检查 TS 格式是否变了"
    missing = sorted(set(src) - set(ts))
    extra = sorted(set(ts) - set(src))
    assert not missing and not extra, f"码表副本与 guji-manager 不一致：缺 {missing}，多 {extra}；重新导出并 build 前端"
    diff = sorted(k for k in src if any(ts[k].get(f) != src[k].get(f) for f in ("code", "label", "route", "ui")))
    assert not diff, f"这些原因的 code/label/route/ui 与 guji-manager 不同：{diff}"
