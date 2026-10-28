# -*- coding: utf-8 -*-
"""控制台的测试借 cv 仓的测试设施：`tests/conftest.py`（环境隔离、`ws`/`keben_book` 等夹具、
不许往仓里写的守卫）与 `tests/helpers.py`、`tests/fixtures/` 冻结数据。

所以跑本仓测试要求 open-guji-cv 是**源码安装**（`pip install -e ../open-guji-cv`），
`guji_console.jobs.cv_root()` 找得到它的 `tests/`。控制台测试本来就是从 cv 仓搬来的，
共用一套冻结数据，不另抄一份。
"""
from __future__ import annotations

import importlib.util
import sys

from guji_console.jobs import cv_root

_CV_TESTS = cv_root() / "tests"
if not (_CV_TESTS / "conftest.py").exists():
    raise RuntimeError(f"找不到 cv 的测试设施 {_CV_TESTS}：open-guji-cv 要源码安装（pip install -e）")
sys.path.append(str(_CV_TESTS))          # helpers.py 及 cv 测试模块里的共用夹具（排在本仓 tests/ 之后：同名模块用本仓的）

_spec = importlib.util.spec_from_file_location("_cv_conftest", _CV_TESTS / "conftest.py")
_cv = importlib.util.module_from_spec(_spec)
sys.modules["_cv_conftest"] = _cv
_spec.loader.exec_module(_cv)
globals().update({k: v for k, v in vars(_cv).items() if not k.startswith("__")})
