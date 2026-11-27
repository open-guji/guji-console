# CHANGELOG

## 未发版

- 裁定事件来源（清理计划 2.4，11-27）：Step8 复核台写的 `confirm`（切分缺陷 `api_step8_seg`、复核裁决 `_events_for`）带 `payload.level／by／channel`＝`human／登录 email／console`；`/api/events` 路径由 manager `write_events` 兜底（manager#1179）；`api_harvest` 重编 seq 时带上原事件的 `reviewer`（原来收割后 reviewer 变空）。依赖 manager 门面新增的 `console_api.provenance`。
- 彩图书双层显示（用户 11-17 定：算法走二值，显示尽量彩图，二值出问题处切彩图看）：字块卡切换改成「自动／二值／彩图／灰度」，缺省「自动」＝落进二值体检可疑区的字块给彩图、其余给二值（没写 ink 的老书没有体检，自动＝二值，与以前一样）；`/api/cache/.../char_patch` 加 `src=color|auto`，响应头 `X-Img-Src`；产物叠图加「底图」（彩图／二值／灰度）与「可疑区」开关（`/api/overlay` 的 `bg`、`qc`，缺省不往下传，老 manager 照用）；新增只读 `GET /api/binqc/{book}/{page}`。要 cv#1650、guji-manager#654。
- 待审卡显示待审原因（A31，sheldon 11-03 定 `pending_reason`）：卡片证据栏加一行「原因：…」，悬停看说明；码表 `frontend/src/pendingReasons.ts` 由 cv 导出生成（与网站同一份），认不出的按 unknown；老 cv 不带这个键时不显示。要 cv#964。

## 0.1.0（2026-10-28）

- 从 open-guji-cv 拆出（cv 的拆包 C0–C3：#749 设计、#751 门面、#752 断反向依赖、#753 写操作走命令行）。
- `guji console` / `guji runs` 改由本包经入口点 `guji.commands` 提供；另有独立入口 `guji-console`。
- 任务队列（`jobs.py`）的工作目录与 `runs/` 改按 cv 包的位置找（原先按本文件位置推）。
- 启动时核 cv 契约版本（支持 v1）。
- `scripts/report_collate_group.py` 随控制台搬来（它用 step8 路由的函数）。
