#!/usr/bin/env python3
"""Probe: R44 — the store economy (a run must not pay a connection per statement).

Measured live before the fix: ONE simple Persian run opened 27 SQLite
connections (a table create, a pragma read, three ALTERs and three index
creates on every RunHistory construction — twice per run — plus a fresh
CREATE per planner_learning call). After batching the hot writers into a
single transaction per logical write and guarding the schema DDL per suite
object, the same run opens 11.

This probe counts the REAL connects and refuses to let the economy rot.
"""

from __future__ import annotations

import sys
from typing import Any

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44 store economy (connections per run):\n")

_BUDGET = 15  # was 27 before the fix; the budget is the point


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import os
    import sqlite3
    import tempfile
    import time
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "economy.db"))

    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        route_and_run("میانگین ۵ و ۷ را حساب کن")  # warm

        orig = sqlite3.connect
        count: dict[str, Any] = {"n": 0}

        def counting(*a: Any, **k: Any) -> Any:
            count["n"] += 1
            return orig(*a, **k)

        sqlite3.connect = counting
        try:
            t0 = time.perf_counter()
            route_and_run("میانگین ۵ و ۷ را حساب کن")
            per = (time.perf_counter() - t0) * 1000
        finally:
            sqlite3.connect = orig

    _ok(f"a simple run stays within {_BUDGET} connections", count["n"] <= _BUDGET,
        f"{count['n']} connects, {per:.0f}ms")
    _ok("the hot path stays inside its 150ms budget", per < 150, f"{per:.0f}ms")

    # The honest guarantee: a recreated database file still gets its schema.
    from universal_mind.run_history import RunHistory

    path = Path(tempfile.mkdtemp()) / "recreated.db"
    first = DatabaseSuite(str(path))
    RunHistory(first).record("فرمان", ["data"], True, excellence=1.0)
    path.unlink()
    second = DatabaseSuite(str(path))
    RunHistory(second).record("فرمان", ["data"], True, excellence=1.0)
    q = second.query("SELECT COUNT(*) AS n FROM run_history")
    _ok("a recreated file really gets its schema back",
        bool(q.get("ok")) and int(q["rows"][0]["n"]) == 1)

    # H4 — scratch hygiene: the leak that once put ~60GB in the temp dir.
    import universal_mind.database_suite as _ds

    scratch_root = Path(tempfile.mkdtemp())
    for name, age in (("um-db-stale", 7200), ("um-db-young", 5)):
        d = scratch_root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "mind.db").write_bytes(b"x")
        old = time.time() - age
        os.utime(d, (old, old))
    with mock_patch("tempfile.gettempdir", lambda: str(scratch_root)):
        reaped = _ds.reap_stale_scratch(force=True)
    _ok("stale scratch is reaped, a live one is not",
        reaped == 1 and not (scratch_root / "um-db-stale").exists()
        and (scratch_root / "um-db-young").exists(), f"{reaped} dir(s)")

    from universal_mind import scheduler as _sched
    from universal_mind.database_suite import DatabaseSuite as _Suite

    store = Path(tempfile.mkdtemp())
    for i in range(5):
        (store / f"mind.db.bak-2026010{i}-000000").write_bytes(b"old")
    conn = sqlite3.connect(str(store / "mind.db"))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.close()
    with mock_patch.object(_Suite, "DEFAULT_DB_DIR", store), \
         mock_patch("sqlite3.connect", side_effect=OSError("No space left on device")):
        failed = _sched.backup_database(keep=2)
    left = list(store.glob("mind.db.bak-2*"))
    _ok("a failed backup still prunes (no junk pile)",
        failed["ok"] is False and len(left) == 2, f"{len(left)} left")

    sys.stderr.write("R44 store economy: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
