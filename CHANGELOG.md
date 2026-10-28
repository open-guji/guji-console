# CHANGELOG

## 0.1.0（2026-10-28）

- 从 open-guji-cv 拆出（cv 的拆包 C0–C3：#749 设计、#751 门面、#752 断反向依赖、#753 写操作走命令行）。
- `guji console` / `guji runs` 改由本包经入口点 `guji.commands` 提供；另有独立入口 `guji-console`。
- 任务队列（`jobs.py`）的工作目录与 `runs/` 改按 cv 包的位置找（原先按本文件位置推）。
- 启动时核 cv 契约版本（支持 v1）。
- `scripts/report_collate_group.py` 随控制台搬来（它用 step8 路由的函数）。
