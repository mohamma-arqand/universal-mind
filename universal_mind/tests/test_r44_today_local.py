"""Tests: R44 — «امروز» means the OPERATOR's today, not UTC's.

The run store keeps `created_at` in UTC (SQLite CURRENT_TIMESTAMP). The
"today" questions must therefore convert it to LOCAL time before comparing,
or every morning between 00:00 and 03:30 (UTC+3:30) the platform denies
work it really did. This was a live bug; these laws keep it dead.
"""

from __future__ import annotations

import datetime as _dt
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch


def _seed_run_utc(db: Any, command: str, utc_ts: str) -> None:
    """Insert one run with an EXPLICIT UTC stamp — no clock involved."""
    db.execute(
        "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
        f"VALUES ('{command}', 'data', 1, 1.0, '{utc_ts}')"
    )


class TestTodayIsTheOperatorsDay:
    """A run stored on the previous UTC day still counts as today locally."""

    def test_the_early_morning_run_really_counts(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "tz.db"))
        RunHistory(iso)  # creates the table with its real schema
        # TIME-INDEPENDENT law: pick the instant that falls on the same LOCAL
        # day but a DIFFERENT UTC day (just after local midnight east of UTC,
        # just before it west of UTC). A naive date(created_at) comparison
        # misses this run at ANY hour; the local-corrected query always sees it.
        offset = _dt.datetime.now() - _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        today = _dt.datetime.now().date()
        t_local = _dt.datetime.combine(
            today, _dt.time(0, 30) if offset >= _dt.timedelta(0) else _dt.time(23, 30)
        )
        utc_stamp = t_local - offset  # the very same instant, expressed in UTC
        _seed_run_utc(iso, "کار امروز", utc_stamp.strftime("%Y-%m-%d %H:%M:%S"))
        # prove the fixture really discriminates (else the law proves nothing)
        assert utc_stamp.date() != today, "fixture must cross the UTC day boundary"

        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("امروز چی کار کردی؟")

        assert "فرمان اجرا کردم" in p["agent_report"], p["agent_report"]

    def test_every_today_query_converts_to_local(self) -> None:
        """No 'today' query may compare a bare UTC stamp against the local date."""
        root = Path(__file__).resolve().parent.parent
        for name in ("reflexive.py", "superplatform_dashboard.py"):
            src = (root / name).read_text(encoding="utf-8")
            assert "date(created_at) = date('now'" not in src, name
            assert "date(created_at) AS d" not in src, name
            assert "date(created_at, 'localtime')" in src, name
