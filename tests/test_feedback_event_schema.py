"""人裁事件规范（doc/formats/人裁事件规范.md）落到代码的几条：

- 「后到覆盖」一律按 `replay_key` = (ts, batch, seq)，不按批次名；
- `target.book/page/col/slot` 全空时构造事件就从 key 补（写入口统一；老数据 10-21 已迁）；
- `resolve` 能按 kind/unit 过滤（切线与定字 key 同形）；
- 控制台写入 `client_ts` 一律毫秒；
- `guji events lint` 的几类问题。
"""

from __future__ import annotations


from open_guji_cv.feedback.events import EventTarget, make_event


def _cut(batch, seq, ts, y):
    return make_event(batch, seq, "cutline",
                      EventTarget(step="row_segment", unit="boundary", key="vol02:5:8:14"),
                      {"y": y, "y_old": 100, "verdict": "moved"}, ts=ts)


def _confirm(batch, seq, ts, shape, key="vol02:5:8:14"):
    return make_event(batch, seq, "confirm", EventTarget(step="seed_admit", unit="cell", key=key),
                      {"v": "confirm", "shape": shape}, ts=ts)


def test_api_events_writes_client_ts_in_ms(tmp_path, monkeypatch):
    from guji_console import deps
    from guji_console.auth import Identity
    from guji_console.routers import feedback as mod
    for key in ("feedback", "batches", "dataset"):
        monkeypatch.setitem(deps._roots, key, tmp_path / key)
    for cached in ("_log", "_batches", "_gold"):
        monkeypatch.setattr(deps, cached, None)
    req = mod.EventsIn(batch="vol02-jiazhu", step="seed_admit", unit="cell", kind="confirm", consume=False,
                       events=[{"id": "vol02:4:1:3", "v": "confirm", "shape": "之", "client_ts": 1788741500.438},
                               {"id": "vol02:4:1:4", "v": "confirm", "shape": "乎", "client_ts": 1788741500438}])
    mod.api_events(req, identity=Identity(email="t@example.com", role="reviewer", tier="reviewer"))
    got = [e.payload["client_ts"] for e in deps.event_log().read("vol02-jiazhu")]
    assert got == [1788741500438, 1788741500438]


