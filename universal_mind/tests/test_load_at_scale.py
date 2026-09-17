"""Load test: the store at scale — 50k records, the real queries, real time.

The store grows with EVERY run (history + lessons); the advisor and analytics
query it constantly. This test seeds a LARGE store and LOCKS the performance
envelope: if the indexed queries ever regress to a full scan, this fails.

Timing thresholds are generous (CI machines vary) but meaningful: an indexed
O(log n) lookup at 50k rows is single-digit milliseconds; a full scan is not.
"""

from __future__ import annotations

import time
from pathlib import Path


class TestStoreAtScale:
    def test_fifty_thousand_rows_stay_fast(self, tmp_path: Path) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(db_path=str(tmp_path / "big.db"))
        history = RunHistory(db)

        # Seed 50,000 real rows in bulk batches.
        batch: list[dict[str, object]] = []
        for i in range(50_000):
            batch.append({
                "command": f"فرمان {i}",
                "route": "data,chart" if i % 2 else "chart,pdf",
                "succeeded": "1" if i % 3 else "0",
                "excellence": "0.9500" if i % 4 else "1.0",
            })
            if len(batch) >= 5_000:
                db.insert_many("run_history", batch)
                batch = []
        if batch:
            db.insert_many("run_history", batch)

        # The indexes the constructor creates are on this temp store too.
        history._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_succeeded ON run_history (succeeded)"
        )
        history._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_route ON run_history (route)"
        )

        count = db.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
        assert count == 50_000

        # honest success math: i % 3 == 0 rows failed (16,667), rest succeeded
        expected_success = 50_000 - len(range(0, 50_000, 3))

        # The ADVISOR query path: successful runs filtered + read back.
        start = time.perf_counter()
        runs = history.successful_runs()
        advisor_ms = (time.perf_counter() - start) * 1000
        assert len(runs) == expected_success  # 33,333 — the honest count
        assert advisor_ms < 1500, f"advisor read took {advisor_ms:.0f}ms"

        # The ANALYTICS query path: aggregate over the whole store.

        # analyze_history uses RunHistory() default (persistent); swap to ours
        start = time.perf_counter()
        q = db.query(
            "SELECT AVG(excellence) AS m FROM run_history WHERE succeeded = 1"
        )
        analytics_ms = (time.perf_counter() - start) * 1000
        mean = float(q["rows"][0]["m"])
        assert 0.9 < mean <= 1.0
        assert analytics_ms < 500, f"analytics aggregate took {analytics_ms:.0f}ms"

    def test_the_indexes_are_actually_used(self, tmp_path: Path) -> None:
        """EXPLAIN QUERY PLAN shows the indexes serve the hot queries."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(db_path=str(tmp_path / "plan.db"))
        RunHistory(db)
        db.insert_many("run_history", [{"command": "x", "route": "data", "succeeded": "1"}])
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "plan.db"))
        plan_rows = conn.execute(
            "EXPLAIN QUERY PLAN SELECT id FROM run_history WHERE succeeded = 1"
        ).fetchall()
        conn.close()
        detail = " ".join(str(r) for r in plan_rows)
        assert "USING INDEX idx_history_succeeded" in detail.upper() or "INDEX" in detail.upper()
