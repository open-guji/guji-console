# -*- coding: utf-8 -*-
"""控制台只许经门面 `open_guji_cv.console_api` 用 cv（设计：cv doc/design/拆分-控制台独立成包与上网站.md 第四节）。

只做静态扫描，含函数内的惰性 import。要用 cv 里新东西：先在 cv 的门面 `_EXPORTS` 登记；
会写工作区（事件以外）或耗时的动作不进门面，走命令行（`guji_console/cli.py::run_guji`）。
"""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "guji_console"
ALLOWED = {"open_guji_cv.console_api"}


def test_console_only_imports_the_facade():
    bad = []
    for p in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                mods = [node.module or ""]
            else:
                continue
            for m in mods:
                if (m == "open_guji_cv" or m.startswith("open_guji_cv.")) and m not in ALLOWED:
                    bad.append(f"{p.relative_to(PKG)}:{node.lineno} {m}")
    assert not bad, "控制台只许 from open_guji_cv.console_api import …：\n  " + "\n  ".join(bad)


def test_facade_names_used_by_console_exist():
    import open_guji_cv.console_api as facade
    used = set()
    for p in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "open_guji_cv.console_api":
                used |= {a.name for a in node.names}
    missing = sorted(used - set(facade.__all__))
    assert not missing, f"控制台用到、门面里没有的名字（cv 版本太旧？）：{missing}"
