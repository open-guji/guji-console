"""CLI 带 book 的命令必填 `-w/--workspace`（2026-09-20，用户定）。

`GUJI_WORKSPACE` 环境变量漏设/设错都不报错：漏设时册定义找不到（好歹会炸），设错时
产物静默写到别的工作区。一天里两次栽在这上面之后改成显式参数：不给就在 argparse 层报错，
给了就校验目录里有这册书的定义，再写进环境变量供下游用。
"""

from __future__ import annotations

import argparse


from open_guji_cv import cli_v2


def _parser():
    parser = argparse.ArgumentParser(prog="guji")
    sub = parser.add_subparsers(dest="command")
    cli_v2.register_subcommands(sub)
    return parser


def test_job_argv_carries_workspace():
    from guji_console.jobs import JobSpec
    spec = JobSpec(pipeline="keben_body_v2", book="bxgb", pages="all", workspace="D:/ws")
    argv = spec.argv()
    assert "--workspace" in argv and argv[argv.index("--workspace") + 1] == "D:/ws"
