#!/usr/bin/env python3
"""Probe: R44 item 13 — the heartbeat HISTORY, asked live.

The old ``tick_health`` only knew "now" (one run in the last 25 hours?). The
operator's real question is «چند روز است زنده؟». This probe proves the answer
on the REAL store (a live witness) and every law on a synthetic one:

1. The live question through the real router answers with a real streak.
2. An empty today never breaks a live streak (not dead at 09:00).
3. A silent day is a zero row, never a missing one — and is NAMED.
4. A dead store says so honestly.
"""

from __future__ import annotations

import sys
from typing import Any

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-13 (the heartbeat history):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def _store_with_days(backs: tuple[int, ...]) -> Any:
    import datetime as dt
    import tempfile
    from pathlib import Path

    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "pulse.db"))
    RunHistory(db)
    now = dt.datetime.now()
    for back in backs:
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
            f"VALUES ('x', 'data', 1, 1.0, '{ts}')"
        )
    return db


def main() -> int:
    # L1 — the LIVE question, real store, real router.
    from universal_mind.persian_router import route_and_run

    live = route_and_run("چند روز است زنده؟")
    _ok("the live question is a reflexive answer", live.get("route") == ["reflexive"],
        f"route={live.get('route')}")
    report = str(live.get("agent_report"))
    _ok("the live answer carries a real streak", "زنده" in report, report[:80])

    # L2 — the laws, on a store where the days are known exactly.
    from universal_mind.tick_pulse import pulse_report, pulse_sentence, pulse_window
    from universal_mind.tick_pulse import alive_streak

    db = _store_with_days((1, 2, 3))  # nothing today, three full days before
    win = pulse_window(days=7, db=db)
    _ok("an empty today does not break the streak", alive_streak(win) == 3,
        f"streak={alive_streak(win)}")

    db2 = _store_with_days((0, 3))
    rep = pulse_report(db=db2)
    _ok("a silent day is a zero row, never a gap",
        len(rep["days"]) == 7 and any(not d["awake"] for d in rep["days"]))
    sentence = pulse_sentence(rep)
    _ok("the silent days are named, not hidden",
        "سکوت" in sentence and all(day in sentence for day in rep["silent"]),
        sentence[:80])

    db3 = _store_with_days(())
    dead = pulse_sentence(pulse_report(db=db3))
    _ok("a dead heartbeat says so", "قطع" in dead, dead[:80])

    sys.stderr.write("R44-13: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
