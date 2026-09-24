"""Tests: R44 — the store economy (a run must not pay 27 connections).

Measured live: one simple Persian run opened 27 SQLite connections — a table
create, a pragma read, three ALTERs and three index creates on EVERY
RunHistory construction (twice per run), plus a fresh CREATE on every
planner_learning call. The hot path budget is a real gate; these laws keep
the economy from silently rotting back.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch


class _ConnectCounter:
    """Count every sqlite3.connect made inside the block."""

    def __enter__(self) -> "_ConnectCounter":
        self.n = 0
        self._orig = sqlite3.connect

        def counting(*a: Any, **k: Any) -> Any:
            self.n += 1
            return self._orig(*a, **k)

        sqlite3.connect = counting
        return self

    def __exit__(self, *exc: Any) -> None:
        sqlite3.connect = self._orig


class TestTheHotPathEconomy:
    """A simple run's connection count is bounded and stays bounded."""

    def test_one_simple_run_is_cheap(self) -> None:
        import tempfile

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "econ.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            route_and_run("میانگین ۵ و ۷ را حساب کن")  # warm (schema, caches)
            with _ConnectCounter() as c:
                route_and_run("میانگین ۵ و ۷ را حساب کن")
        # 27 was the measured cost before the fix; the budget is the point.
        assert c.n <= 15, f"a simple run opened {c.n} connections"


class TestTheSchemaMemo:
    """ensure_schema runs once per file, and is honest when the file changes."""

    def test_the_second_call_does_not_reconnect(self, tmp_path: Path) -> None:
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite(str(tmp_path / "memo.db"))
        ddl = ["CREATE TABLE IF NOT EXISTS memo_probe (x INTEGER)"]
        assert db.ensure_schema("memo_probe", ddl) is True
        with _ConnectCounter() as c:
            assert db.ensure_schema("memo_probe", ddl) is False
        assert c.n == 0, "the memoized call must not touch the database"
        with _ConnectCounter() as c:
            assert db.ensure_schema("memo_probe", ddl) is False
        assert c.n == 0

    def test_a_replaced_file_gets_its_schema_back(self, tmp_path: Path) -> None:
        """The guarantee: memoization must never leave a fresh file bare."""
        from universal_mind.database_suite import DatabaseSuite

        path = tmp_path / "replaced.db"
        db = DatabaseSuite(str(path))
        ddl = ["CREATE TABLE IF NOT EXISTS memo_probe (x INTEGER)"]
        assert db.ensure_schema("memo_probe", ddl) is True
        # Replace the file entirely (a test recreating its temp database):
        path.unlink()
        fresh = DatabaseSuite(str(path))
        assert fresh.ensure_schema("memo_probe", ddl) is True
        q = fresh.query("SELECT name FROM sqlite_master WHERE name = 'memo_probe'")
        assert q["ok"] and q["rows"], "the recreated file must really have the table"

    def test_the_run_store_is_never_left_bare(self, tmp_path: Path) -> None:
        """A brand-new database can still be written to right away."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(str(tmp_path / "fresh.db"))
        RunHistory(db).record("فرمان", ["data"], True, excellence=1.0)
        q = db.query("SELECT COUNT(*) AS n FROM run_history")
        assert q["ok"] and int(q["rows"][0]["n"]) == 1
