# -*- coding: utf-8 -*-
"""并进 `guji` 的两条子命令：`guji console`（起控制台）与 `guji runs`（看控制台的任务队列）。

入口点组 `guji.commands`（见 open-guji-cv `cli_v2.load_plugin_commands`）：装了本包，`guji` 就多这两条；
本包也有自己的入口 `guji-console`（等同 `guji console`）。命令原在 cv 的 `cli_v2.py`，
控制台拆成独立包时（cv doc/design/拆分-控制台独立成包与上网站.md C3）搬来，参数与行为不变。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_PORT = 8640

#: 本版控制台认的 pipeline 契约版本（cv `core/contract.py::CONTRACT_VERSION`，doc/契约.md）
SUPPORTS_CONTRACT = (1,)


def _check_contract() -> None:
    from open_guji_cv.console_api import CONTRACT_VERSION
    if CONTRACT_VERSION not in SUPPORTS_CONTRACT:
        print(f"✗ 装着的 open-guji-cv 讲契约 v{CONTRACT_VERSION}，本版 guji-console 只认 {SUPPORTS_CONTRACT}；"
              "升级 guji-console 或换一版 cv。", file=sys.stderr)
        sys.exit(1)


def _out(d) -> None:
    """统一出 JSON。管道接 jq 用。"""
    print(json.dumps(d, ensure_ascii=False, indent=1, default=str))


def cmd_console(args) -> None:
    _check_contract()
    from .app import serve
    from .auth import config as auth_config

    host = getattr(args, "host", None) or "127.0.0.1"
    loopback = host in ("127.0.0.1", "localhost")
    # 环境变量 GUJI_CONSOLE_NO_AUTH / GUJI_CONSOLE_DEV_IDP 与命令行参数等价（原来命令行
    # 那一步会把环境变量的值覆盖成 False，环境变量形同虚设）。
    no_auth = bool(getattr(args, "no_auth", False)) or auth_config.get().no_auth
    if no_auth and not loopback:
        print(f"✗ --no-auth 只能在本机（127.0.0.1/localhost）用，绑 {host} 时必须过身份接口鉴权，"
              "拒绝启动——对外开放校对平台不能关掉登录。", file=sys.stderr)
        sys.exit(1)
    root_path = getattr(args, "root_path", "") or ""
    dev_idp = bool(getattr(args, "dev_idp", False)) or auth_config.get().dev_idp
    auth_config.set_config(no_auth=no_auth, root_path=root_path, dev_idp=dev_idp)

    # 向后兼容（协调者 09-26 20:10 验收意见）：OAuth 还没配（网站两个端点
    # 10 月上旬才有 PR），服务器的 systemd 单元现在起控制台**没带任何鉴权参数**。
    # 不补这条的话，这次改动一合 main、服务器一重启，控制台就变成一个当下
    # 用不了的登录页，把正在用的人全挡在外面。
    oauth_configured = bool(auth_config.get().client_secret)
    # 设了 GUJI_OAUTH_REDIRECT_URI 说明这是对外部署（前面有反代）：反代过来的请求
    # 来源都是 127.0.0.1，「本机就自动免鉴权」会把 admin 开给公网（服务器值守
    # 09-27 #109 实测）。这时密钥为空不许悄悄退回免鉴权，要免鉴权必须显式声明。
    public_deploy = bool(auth_config.get().redirect_uri)
    if not no_auth and not dev_idp and not oauth_configured:
        if loopback and public_deploy:
            print("✗ 设了 GUJI_OAUTH_REDIRECT_URI（对外部署）但 GUJI_OAUTH_CLIENT_SECRET 为空——"
                  "反代后的请求都来自本机，自动免鉴权会把 admin 开给外网，拒绝启动。"
                  "要么填好 OAuth 密钥；要么前面另有一层鉴权时显式设 GUJI_CONSOLE_NO_AUTH=1。",
                  file=sys.stderr)
            sys.exit(1)
        if loopback:
            no_auth = True
            auth_config.set_config(no_auth=True)
            print("  ⚠️⚠️  未配置 OAuth（GUJI_OAUTH_CLIENT_SECRET 为空）且未加 --dev-idp/--no-auth，"
                  "绑的是本机地址——按本机免鉴权运行。生产部署前必须配置 OAuth 或显式加"
                  " --no-auth/--dev-idp。\n")
        else:
            print(f"✗ 绑 {host} 但没配置 OAuth（GUJI_OAUTH_CLIENT_SECRET 为空）也没加 --dev-idp——"
                  "登录流程打不通，拒绝启动。要么配好 OAuth，要么本机开发用 --dev-idp。",
                  file=sys.stderr)
            sys.exit(1)

    # 工作区总目录（2026-09-30）：控制台进程没有「默认工作区」，工作区在页面里选（浏览器的状态）。
    # 旧法是用 GUJI_WORKSPACE 指到某一本书的目录、再扫它的兄弟——重启时带错一本，下拉框与册列表
    # 就对不上，已删。这里把继承来的 GUJI_WORKSPACE 摘掉，免得悄悄成为「请求没带工作区时的默认」。
    from open_guji_cv.console_api import ROOT_ENV, discover_workspaces
    wroot = getattr(args, "workspaces_root", None) or os.environ.get(ROOT_ENV)
    if not wroot or not Path(wroot).expanduser().is_dir():
        print(f"✗ 要给工作区总目录：guji console --workspaces-root D:/workspace/guji-workspace\n"
              f"  （或设环境变量 {ROOT_ENV}）。给的是：{wroot!r}", file=sys.stderr)
        sys.exit(1)
    os.environ[ROOT_ENV] = str(Path(wroot).expanduser().resolve())
    if os.environ.pop("GUJI_WORKSPACE", None):
        print("  （已忽略环境变量 GUJI_WORKSPACE：控制台不再有默认工作区，请在页面里选。）")
    print(f"  工作区总目录  {os.environ[ROOT_ENV]}")
    for w in discover_workspaces():
        print(f"    - {w['id']:14} {len(w['books'])} 册  {w['name']}")
    if not discover_workspaces():
        print("  ⚠️  总目录下没有带 books/ 的子目录，页面上没有工作区可选。")
    if no_auth:
        print("  ⚠️  --no-auth：鉴权已关闭，任何能连上本机端口的人都能起跑批、写裁决——"
              "只许本机开发用。\n")
    if dev_idp:
        print("  ⚠️  --dev-idp：登录走本机假登录页，不是网站真授权——只许本机开发用。\n")
    serve(port=args.port, open_browser=not args.no_browser, host=host, root_path=root_path)


def cmd_runs(args) -> None:
    """控制台的任务队列：list | show | cancel | log。

    队列是**控制台进程内**的（`console/jobs.py` 的单 worker），所以这几条读的是
    它落在 `runs/` 下的记录。控制台没在跑的时候 list 是空的，这不是错。
    """
    from .jobs import JobRunner
    runner = JobRunner()
    if args.action == "list":
        _out(runner.list(args.limit))
    elif args.action == "show":
        job = runner.get(args.id)
        if not job:
            print("没有这个任务"); sys.exit(1)
        _out(job.to_dict())
    elif args.action == "cancel":
        _out({"ok": runner.cancel(args.id)})
    elif args.action == "log":
        f = runner.log_path(args.id)
        if not f.exists():
            print("还没有日志"); sys.exit(1)
        if not args.follow:
            print(f.read_text(encoding="utf-8", errors="replace"), end="")
            return
        from .sse import tail_job
        for ev in tail_job(runner, args.id):
            if ev is None:
                continue
            print(ev.get("line") or f"[{ev['type']}]", flush=True)
            if ev["type"] in ("complete", "error"):
                return


def add_console_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("console", help="启动控制台（FastAPI；guji-console 提供）")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--host", default="127.0.0.1",
                   help="监听地址，默认 127.0.0.1（对外开放校对平台生产环境仍应绑回环地址，"
                        "由反向代理转发，见 overview 总览/16）")
    p.add_argument("--no-auth", action="store_true",
                   help="关掉鉴权（本机开发用）。只在 --host 是 127.0.0.1/localhost 时允许，"
                        "绑别的地址会拒绝启动")
    p.add_argument("--root-path", default="",
                   help="挂在反向代理前缀下时用，如 /collate（网站把 /collate/* 转发到这里）")
    p.add_argument("--workspaces-root", default=None,
                   help="工作区总目录（如 D:/workspace/guji-workspace）：其下有 books/ 的子目录都是可选工作区，"
                        "在页面里选；缺省读环境变量 GUJI_WORKSPACES_ROOT。控制台进程没有默认工作区")
    p.add_argument("--dev-idp", action="store_true",
                   help="登录走本机假登录页，不打网站真的 /oauth/authorize|token（网站两个端点"
                        "10 月上旬才有 PR，本机开发/测试先用这个）。跟 --no-auth 不是一回事："
                        "这个仍然走一遍完整的 OAuth 回调，只是身份接口是假的")


def add_runs_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("runs", help="控制台任务：list | show | cancel | log（guji-console 提供）")
    p.add_argument("action", choices=["list", "show", "cancel", "log"])
    p.add_argument("id", nargs="?", default=None)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("-f", "--follow", action="store_true", help="log：跟着刷")


COMMANDS = {
    "console": (add_console_parser, cmd_console),
    "runs": (add_runs_parser, cmd_runs),
}


def main(argv: list[str] | None = None) -> None:
    """`guji-console …` = `guji console …`。"""
    ap = argparse.ArgumentParser(prog="guji-console", description="open-guji 控制台")
    sub = ap.add_subparsers(dest="cmd")
    add_console_parser(sub)
    add_runs_parser(sub)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("console", "runs"):
        argv = ["console", *argv]
    args = ap.parse_args(argv)
    COMMANDS[args.cmd][1](args)
