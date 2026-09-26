"""Tests: R44/R48 — «امروز» means the OPERATOR's today, not UTC's.

`created_at` is STORED local (datetime.now() in the writer), so the
reader must NOT apply a SECOND 'localtime' — the old double shift pushed
every evening run into tomorrow (a live bug caught by an after-20:30
verify). These laws keep the single-shift truth dead-anchored.
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
        # THE TRUE LAW (R48 fix): `record()` stores created_at in LOCAL time
        # (datetime.now()), so the reader compares the bare local stamp with
        # the local 'now'. A run made at 00:30 local — which falls on the
        # PREVIOUS UTC day east of UTC — must still count as today. Seeding
        # with the WRITER's own stamp format (local) is what reality produces;
        # a UTC stamp would be a fictional premise (the double-shift bug).
        offset = _dt.datetime.now() - _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        today = _dt.datetime.now().date()
        t_local = _dt.datetime.combine(
            today, _dt.time(0, 30) if offset >= _dt.timedelta(0) else _dt.time(23, 30)
        )
        # discrimination proof: the same instant on a different UTC day
        utc_equiv = t_local - offset
        assert utc_equiv.date() != today, "fixture must cross the UTC day boundary"
        _seed_run_utc(iso, "کار امروز", t_local.strftime("%Y-%m-%d %H:%M:%S"))

        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("امروز چی کار کردی؟")

        assert "فرمان اجرا کردم" in p["agent_report"], p["agent_report"]

    def test_every_today_query_reads_local_stamps_verbatim(self) -> None:
        """created_at is STORED local (datetime.now() / one SQL 'localtime'),
        so readers must NOT apply a SECOND 'localtime' — that shifted every
        evening run into tomorrow (caught live by an after-20:30 verify)."""
        root = Path(__file__).resolve().parent.parent
        for name in ("reflexive.py", "superplatform_dashboard.py"):
            src = (root / name).read_text(encoding="utf-8")
            assert "date(created_at, 'localtime')" not in src, name
            assert "date(created_at) = date('now'" in src or \
                "date(created_at) AS d" in src, name
