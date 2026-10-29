# guji-console

open-guji 的控制台：看产物与叠图、人裁（定字、切线、版框、列……）、看评测、下单跑管线的 Web 界面。
后端 FastAPI（`guji_console/`），前端 React + Vite（`guji_console/frontend/`，构建产物进 `guji_console/static/dist/`）。

2026-10-28 从 [open-guji-cv](https://github.com/open-guji/open-guji-cv) 的 `open_guji_cv/console/` 拆出来，带着那个目录的提交历史。
设计与分步见 cv 仓 `doc/design/拆分-控制台独立成包与上网站.md`。

## 和 cv 的关系

- **读、现算图、写人裁事件**：只经 cv 的门面 `open_guji_cv.console_api`，不 import cv 的其它内部（守卫：`tests/test_facade_only.py`）。
- **会改东西或耗时的动作**（跑管线、消费事件、导金标、迁载体、漂移检查、跑评测）：起子进程调 cv 命令行（`guji_console/jobs.py`、`guji_console/cli.py`）。
- 启动时核 cv 的契约版本（`guji_console/commands.py::SUPPORTS_CONTRACT`）。
- cv 不依赖本包。

## 安装与启动

与 cv 装在同一个环境，cv 用源码安装：

```bash
uv pip install -e ../open-guji-cv[torch,dev] -e ".[dev]"
guji console --no-auth --workspaces-root D:/workspace/guji-workspace     # 本机
guji-console --no-auth --workspaces-root …                               # 同上，独立入口
guji runs list                                                            # 看控制台的任务队列
```

装上本包后，`guji console` / `guji runs` 由本包经入口点 `guji.commands` 提供（以前在 cv 的 `cli_v2.py` 里，参数不变）。
鉴权、对外部署的参数见 `guji_console/auth/config.py` 与 cv 仓 `doc/console_manual.md`。

## 线上（console.kaiyuanguji.com）

对外跑的那份用网站 OAuth 登录（`client_id=collate`），不许 `--no-auth`。额外两个环境变量：

| 变量 | 作用 |
|---|---|
| `GUJI_CONSOLE_MIN_TIER=admin` | 只让网站管理员进（第一阶段，Sheldon 10-29）；缺省 `reviewer`，校对者也能进 |
| `GUJI_CONSOLE_NO_RUNS=1` | 不收「下单跑管线」，产物由整理的人打包送上来 |

所有人在审卡上的裁决都直接落人裁事件，事件里记登录的 email。设计见 cv 仓 `doc/design/拆分-控制台独立成包与上网站.md` 与本仓 `docs/上网站设计.md`。

## 前端

```bash
cd guji_console/frontend && npm ci && npm run build      # 出到 ../static/dist
```

## 测试

```bash
python -m pytest -q -n auto
```

测试借 cv 仓的 `tests/conftest.py`、`tests/helpers.py` 与 `tests/fixtures/`（都是从 cv 搬来的测试，共用同一套冻结数据），
所以 cv 必须是源码安装。几条前端口径测试要 node ≥ 22.6（`--experimental-strip-types`），没有就跳过。
