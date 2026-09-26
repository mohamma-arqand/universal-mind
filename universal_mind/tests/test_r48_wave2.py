"""R48 wave 2 — the clear-eyed path: pooled reads, excellence-aware
prediction, and a gate that leaves its stamp.

Item 5: SELECTs ride one pooled reader — no per-query connection churn.
Item 6: the index decision is MEASURED (a 0.14ms SCAN beats an index's
       permanent write tax at this scale) — the churn was the bottleneck.
Item 7: the predictor blends success rate with MEAN EXCELLENCE — a
       thin-evidence chain earns a lower tier than a rich one.
Item 8: every gated run carries gate_outcome ('passed'/'repaired'/
       'weak_shipped') into history — countable, speakable.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db(rows: list[dict[str, Any]] | None = None) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r48w2.db"))
    RunHistory(suite)
    if rows:
        suite.insert_many("run_history", rows)
    return suite


class TestReadPool:
    def test_persistent_selects_reuse_one_connection(self) -> None:
        # the hot path is the PERSISTENT store — that one pools a reader
        import tempfile as _tf

        suite = DatabaseSuite(str(Path(_tf.mkdtemp()) / "r48pool.db"),
                              persistent=True)
        RunHistory(suite)
        opened: list[int] = []
        orig = sqlite3.connect

        def spy(*a: Any, **k: Any) -> Any:
            opened.append(1)
            return orig(*a, **k)

        with patch.object(sqlite3, "connect", spy):
            for _ in range(10):
                q = suite.query("SELECT COUNT(*) AS n FROM run_history")
                assert q["ok"] is True
        # 10 reads, at most ONE fresh connection (the pooled reader)
        assert len(opened) <= 1
        suite.close_reader()

    def test_temp_stores_never_lock_the_file(self) -> None:
        # R48 hotfix: a pooled handle LOCKS the file on Windows — temp
        # stores (tests, probes) must ride the closed-per-use path so any
        # later unlink() succeeds. The pool is a lens, never a blocker.
        suite = _db()
        for _ in range(3):
            q = suite.query("SELECT COUNT(*) AS n FROM run_history")
            assert q["ok"] is True
        # no pooled entry for a temp path
        assert suite.db_path not in type(suite)._read_pool
        # and the file stays deletable — the law the live probe caught
        suite.close_reader()
        Path(suite.db_path).unlink()

    def test_reads_see_committed_writes(self) -> None:
        suite = _db()
        suite.insert_many("run_history", [
            {"command": "x", "route": "r", "succeeded": 1, "excellence": 0.9}])
        q = suite.query("SELECT COUNT(*) AS n FROM run_history")
        assert q["rows"][0]["n"] == 1  # write committed → pool reads it
        suite.close_reader()

    def test_broken_pool_falls_back_to_closed_handle(self) -> None:
        suite = _db()
        # poison the pool with a closed connection
        bad = sqlite3.connect(suite.db_path)
        bad.close()
        type(suite)._read_pool[suite.db_path] = bad
        q = suite.query("SELECT COUNT(*) AS n FROM run_history")
        assert q["ok"] is True  # the fallback path answered
        suite.close_reader()


class TestExcellenceAwarePredictor:
    def test_thin_evidence_earns_a_lower_tier(self) -> None:
        rows = (
            [{"command": "a", "route": "rich", "succeeded": 1,
              "excellence": 1.0} for _ in range(6)]
            + [{"command": "b", "route": "thin", "succeeded": 1,
                "excellence": 0.5} for _ in range(6)]
        )
        db = _db(rows)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.success_predictor import predict_success

            rich = predict_success(("rich",))
            thin = predict_success(("thin",))
        assert rich.tier == "strong" and rich.success_probability >= 0.9
        assert thin.tier != "strong"  # same success rate, thinner excellence
        assert thin.success_probability < rich.success_probability

    def test_the_safety_net_of_laplace_stays(self) -> None:
        db = _db([{"command": "one", "route": "once", "succeeded": 1,
                   "excellence": 0.0}])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.success_predictor import predict_success

            p = predict_success(("once",))
        # 1/1 with zero excellence is never a blind strong
        assert p.tier != "strong"


class TestGateStamp:
    def test_real_runs_carry_gate_outcome(self) -> None:
        db = _db()
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            route_and_run("میانگین ۵ و ۷ را حساب کن")
        q = db.query("SELECT gate_outcome FROM run_history ORDER BY id")
        assert q["rows"] and q["rows"][0]["gate_outcome"] in (
            "passed", "repaired", "weak_shipped")
        db.close_reader()

    def test_gate_outcome_is_countable(self) -> None:
        db = _db()
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            route_and_run("میانگین ۵ و ۷ را حساب کن")
            route_and_run("نمودار خطی از ۲ و ۳ بکش")
        q = db.query("SELECT gate_outcome, COUNT(*) AS n FROM run_history "
                     "GROUP BY gate_outcome")
        stamped = sum(int(r["n"]) for r in q["rows"]
                      if r["gate_outcome"])
        assert stamped == 2  # both rows carry a stamp
        db.close_reader()
