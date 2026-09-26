"""R48 hotfix — the double-shift time bomb (a live product bug).

created_at is STORED in local time (datetime.now() in the writer), but
every reader applied a SECOND 'localtime' in SQL — pushing every run
made after ~20:30 local into TOMORROW's bucket. The verify that caught
it ran at 22:31 and heard «سکوت» about a day that had 2 real runs.

These tests pin the single-shift law at the WRITER's format: evening
runs stay today, morning-crossing runs stay today, and no reader may
apply 'localtime' to created_at a second time.
"""

from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db_with_seed(stamp: str) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r48tz.db"))
    RunHistory(suite)
    suite.execute(
        "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
        f"VALUES ('کار شام','data', 1, 1.0, '{stamp}')"
    )
    return suite


class TestTheDoubleShift:
    """Evening runs belong to TODAY, not tomorrow."""

    def test_an_evening_run_counts_as_today(self) -> None:
        # the writer's own format: LOCAL time, 22:31 — the very stamp that
        # the buggy reader pushed into tomorrow
        stamp = dt.datetime.now().replace(
            hour=22, minute=31, second=0).strftime("%Y-%m-%d %H:%M:%S")
        db = _db_with_seed(stamp)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("امروز چی کار کردی؟")
        assert "فرمان اجرا کردم" in p["agent_report"], p["agent_report"]
        db.close_reader()

    def test_yesterday_answers_from_real_evening_rows(self) -> None:
        db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r48tz2.db"))
        RunHistory(db)
        y = dt.datetime.now() - dt.timedelta(days=1)
        stamp = y.replace(hour=22, minute=31).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
            f"VALUES ('کار شام دیروز','data', 1, 1.0, '{stamp}')"
        )
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("دیروز چی کار کردی؟")
        assert "۱ فرمان" in p["agent_report"], p["agent_report"]
        db.close_reader()

    def test_no_reader_applies_a_second_localtime(self) -> None:
        """The law itself: created_at is local; readers must not re-shift."""
        root = Path(__file__).resolve().parent.parent
        for name in ("time_windows.py", "reflexive.py", "advisor_suggest.py",
                     "history_compact.py", "superplatform_dashboard.py",
                     "tick_pulse.py", "weekly_letter.py", "yearbook.py"):
            src = (root / name).read_text(encoding="utf-8")
            assert "created_at, 'localtime'" not in src, (
                f"{name} applies a second 'localtime' to a local stamp")

    def test_the_writer_still_stamps_local(self) -> None:
        """The writer's contract: created_at == local wall-clock time."""
        import re

        src = (Path(__file__).resolve().parent.parent
               / "run_history.py").read_text(encoding="utf-8")
        # the writer stamps with local now(), not utcnow()
        assert re.search(r'created_at.*?_dt\.now\(\)\.strftime', src), (
            "the writer must keep stamping LOCAL time (datetime.now())")

