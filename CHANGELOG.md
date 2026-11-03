# CHANGELOG

## 未发版

- 待审卡显示待审原因（A31，sheldon 11-03 定 `pending_reason`）：卡片证据栏加一行「原因：…」，悬停看说明；码表 `frontend/src/pendingReasons.ts` 由 cv 导出生成（与网站同一份），认不出的按 unknown；老 cv 不带这个键时不显示。要 cv#964。

## 0.1.0（2026-10-28）

- 从 open-guji-cv 拆出（cv 的拆包 C0–C3：#749 设计、#751 门面、#752 断反向依赖、#753 写操作走命令行）。
- `guji console` / `guji runs` 改由本包经入口点 `guji.commands` 提供；另有独立入口 `guji-console`。
- 任务队列（`jobs.py`）的工作目录与 `runs/` 改按 cv 包的位置找（原先按本文件位置推）。
- 启动时核 cv 契约版本（支持 v1）。
- `scripts/report_collate_group.py` 随控制台搬来（它用 step8 路由的函数）。
