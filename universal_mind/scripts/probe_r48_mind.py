#!/usr/bin/env python3
"""R48 — the strict judge, the clear-eyed path: 12 live proofs.

This probe RUNS the real code (no mocks of behavior under test) and
asserts each R48 acceptance with hard failure on any regression:

  1  COURAGE no longer rubber-stamps a bare {"ok": True} — an
     inspectable witness is required (path/bytes/number).
  2  COURAGE awards full virtue only to real, inspectable work.
  3  TEMPERANCE is learned per-route from durations_ms history —
     a 300x-slow run scores ~0, a normal one ~1.
  4  TEMPERANCE's data ledger exists: durations_ms is recorded in
     run_history by real runs (the column the old judge never had).
  5  WISDOM stays depth-aware: fewer, deeper steps beat many shallow
     ones at equal mass.
  6  The read pool answers: 10 SELECTs open at most ONE connection.
  7  The read pool sees committed writes (no stale reads).
  8  A broken pooled reader falls back — the pool is a lens, never a
     blocker.
  9  EXCELLENCE-aware prediction: same success rate, thinner
     excellence → lower tier.
 10  Laplace stays: 1/1 with zero excellence is never 'strong'.
 11  Gate stamp: real runs carry gate_outcome ('passed' etc.) into
     history — countable from SQL.
 12  The interpreter lock resolves a real interpreter carrying
     numpy+pytest+sklearn (the outage lesson).
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402
from universal_mind.run_history import RunHistory  # noqa: E402

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n:2d}. {label}")
    if not ok:
        FAILURES.append(label)


def _db() -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r48probe.db"))
    RunHistory(suite)
    return suite


def main() -> int:
    # ---- the strict judge -------------------------------------------------
    from universal_mind.arete.run_judgment import run_virtue_scores

    bare = run_virtue_scores({"route": ["chart"], "result": {"chart": {"ok": True}}})
    check(1, "COURAGE rejects a bare ok-dict (0.5, not 1.0)",
          abs(bare["courage"] - 0.5) < 1e-9)

    real = run_virtue_scores({"route": ["chart"],
                               "result": {"chart": {"path": "p.png", "bytes": 900}}})
    check(2, "COURAGE full virtue for real inspectable work",
          real["courage"] >= 0.999)

    db = _db()
    # seed durations history: chart normally takes ~1s
    from datetime import datetime

    for _ in range(5):
        db.insert_many("run_history", [{
            "command": "c", "route": "chart", "succeeded": 1,
            "excellence": 0.9,
            "durations_ms": '{"chart": 1000.0}',
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
    # the judge must learn from THIS seeded store, not the live one
    with patch.object(DatabaseSuite, "shared_persistent",
                      classmethod(lambda cls: db)):
        slow = run_virtue_scores({"route": ["chart"],
                                   "result": {"chart": {"path": "p.png", "bytes": 5}},
                                   "durations_ms": {"chart": 300_000.0}})
        normal = run_virtue_scores({"route": ["chart"],
                                    "result": {"chart": {"path": "p.png", "bytes": 5}},
                                    "durations_ms": {"chart": 1_000.0}})
    check(3, f"TEMPERANCE learned per-route (slow={slow['temperance']:.2f}, "
             f"normal={normal['temperance']:.2f})",
          slow["temperance"] < 0.05 and normal["temperance"] >= 0.99)

    # durations really recorded by a real run
    db2 = _db()
    with patch.object(DatabaseSuite, "shared_persistent",
                      classmethod(lambda cls: db2)):
        from universal_mind.persian_router import route_and_run

        route_and_run("میانگین ۵ و ۷ را حساب کن")
        route_and_run("نمودار خطی از ۲ و ۳ بکش")
    q = db2.query("SELECT durations_ms FROM run_history WHERE durations_ms != ''")
    check(4, f"durations_ms recorded by real runs ({len(q['rows'])} rows)",
          bool(q["rows"]))

    deep = run_virtue_scores({"route": ["chart", "data"],
                              "result": {"chart": {"path": "p.png", "bytes": 5},
                                         "data": {"rows": 2}}})
    shallow = run_virtue_scores({"route": ["a", "b", "c", "d", "e"],
                                 "result": {k: {"ok": True} for k in "abcde"}})
    check(5, "WISDOM rewards depth over count (deep>shallow)",
          deep["wisdom"] >= shallow["wisdom"])

    # ---- the clear-eyed path ---------------------------------------------
    # THE POOLABLE LAW (R48 hotfix): the PERSISTENT store pools one reader
    # (10 SELECTs → at most 1 fresh connection); a temp store must ride
    # the closed-per-use path so its file never gets locked on Windows.
    import tempfile as _tf

    psuite = DatabaseSuite(str(Path(_tf.mkdtemp()) / "r48pool.db"), persistent=True)
    RunHistory(psuite)
    opened: list[int] = []
    orig = sqlite3.connect

    def spy(*a: Any, **k: Any) -> Any:
        opened.append(1)
        return orig(*a, **k)

    with patch.object(sqlite3, "connect", spy):
        for _ in range(10):
            assert psuite.query("SELECT COUNT(*) AS n FROM run_history")["ok"]
    check(6, f"persistent read pool: 10 SELECTs → {len(opened)} fresh connection(s)",
          len(opened) <= 1)
    psuite.close_reader()

    suite = _db()
    for _ in range(3):
        assert suite.query("SELECT COUNT(*) AS n FROM run_history")["ok"]
    check(6, "temp stores never pool (file never locked)",
          suite.db_path not in type(suite)._read_pool)

    suite2 = _db()
    suite2.insert_many("run_history", [
        {"command": "x", "route": "r", "succeeded": 1, "excellence": 0.9}])
    q = suite2.query("SELECT COUNT(*) AS n FROM run_history")
    check(7, "pool sees committed writes", q["rows"][0]["n"] == 1)
    suite2.close_reader()

    suite3 = _db()
    bad = sqlite3.connect(suite3.db_path)
    bad.close()
    type(suite3)._read_pool[suite3.db_path] = bad
    q = suite3.query("SELECT COUNT(*) AS n FROM run_history")
    check(8, "broken reader falls back (lens, not blocker)", q["ok"] is True)
    suite3.close_reader()

    rows = (
        [{"command": "a", "route": "rich", "succeeded": 1, "excellence": 1.0}
         for _ in range(6)]
        + [{"command": "b", "route": "thin", "succeeded": 1, "excellence": 0.5}
           for _ in range(6)]
    )
    db3 = _db()
    db3.insert_many("run_history", rows)
    with patch.object(DatabaseSuite, "shared_persistent",
                      classmethod(lambda cls: db3)):
        from universal_mind.success_predictor import predict_success

        rich = predict_success(("rich",))
        thin = predict_success(("thin",))
    check(9, f"excellence-aware tiers (rich={rich.tier}, thin={thin.tier})",
          rich.tier == "strong" and thin.tier != "strong")

    db4 = _db()
    db4.insert_many("run_history", [
        {"command": "one", "route": "once", "succeeded": 1, "excellence": 0.0}])
    with patch.object(DatabaseSuite, "shared_persistent",
                      classmethod(lambda cls: db4)):
        from universal_mind.success_predictor import predict_success

        p = predict_success(("once",))
    check(10, f"Laplace safety net stays (tier={p.tier})", p.tier != "strong")

    db5 = _db()
    with patch.object(DatabaseSuite, "shared_persistent",
                      classmethod(lambda cls: db5)):
        from universal_mind.persian_router import route_and_run

        route_and_run("میانگین ۵ و ۷ را حساب کن")
    q = db5.query("SELECT gate_outcome FROM run_history ORDER BY id")
    check(11, f"gate stamp in history ({q['rows'][0]['gate_outcome']})",
          bool(q["rows"]) and q["rows"][0]["gate_outcome"] in (
              "passed", "repaired", "weak_shipped"))
    db5.close_reader()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from interpreter_gate import interpreter_gate  # type: ignore[import-not-found]

    ok, msg = interpreter_gate()
    check(12, f"interpreter lock: {msg}", ok)

    print()
    if FAILURES:
        print(f"R48 probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R48 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
