"""Tests: R45 wave-1 — time windows and the daily reminder.

Live laws:
1. Time windows read the REAL store with the LOCAL-day law — yesterday's
   runs answer «دیروز», a silent week says so, and honest environment
   refusals never inflate the counts.
2. «یادآور» + a recurring time = a real schedule row (with half/quarter
   hours), not an instant toast; a reminder without a time stays an instant
   toast; the reply names the registered time.
"""

from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from universal_mind.database_suite import DatabaseSuite


@pytest.fixture()  # type: ignore[untyped-decorator]
def seeded_db() -> DatabaseSuite:
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r45w1.db"))
    RunHistory(db)
    now = dt.datetime.now()
    # back, ok, outcome_class — a realistic mixed week
    for back, ok, cls in (
        (0, 1, ""), (0, 1, ""), (1, 1, ""), (1, 0, ""),
        (3, 1, ""), (40, 1, ""), (40, 1, "blocked_env"),
    ):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('seed-x','data',{int(ok)},1.0,'{cls}','{ts}')"
        )
    return db


def _router(db: DatabaseSuite) -> Any:
    from universal_mind.persian_router import route_and_run

    def _run(cmd: str) -> dict[str, Any]:
        # the patch must be alive DURING the call — a with-block that
        # returns a lambda undoes the patch before the lambda ever runs.
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            return route_and_run(cmd)

    return _run


class TestTimeWindows:
    def test_yesterday_answers_from_real_rows(self, seeded_db: DatabaseSuite) -> None:
        run = _router(seeded_db)
        p = run("دیروز چی کار کردی؟")
        assert p["route"] == ["reflexive"]
        assert "۲ فرمان" in p["agent_report"] and "۱ موفق" in p["agent_report"]

    def test_week_window_counts_seven_local_days(self, seeded_db: DatabaseSuite) -> None:
        run = _router(seeded_db)
        p = run("این هفته چطور بود؟")
        assert "۵ فرمان" in p["agent_report"] and "۴ موفق" in p["agent_report"]

    def test_last_week_silence_is_honest(self, seeded_db: DatabaseSuite) -> None:
        run = _router(seeded_db)
        p = run("هفته پیش چه بود؟")
        assert "سکوت" in p["agent_report"]

    def test_month_window_reaches_forty_days_back(self, seeded_db: DatabaseSuite) -> None:
        run = _router(seeded_db)
        p = run("ماه پیش چطور بود؟")
        assert "۱ فرمان" in p["agent_report"]

    def test_env_refusals_never_inflate_windows(self, seeded_db: DatabaseSuite) -> None:
        run = _router(seeded_db)
        p = run("این ماه چطور بود؟")
        # week rows (2+2+1=5) count; the 40-day rows are out of window and
        # the blocked_env row is excluded even where in-window.
        assert "۵ فرمان" in p["agent_report"] and "۴ موفق" in p["agent_report"]


class TestDailyReminder:
    def test_half_hour_daily_reminder_registers(self, tmp_path: Path) -> None:
        from universal_mind.scheduler import _ensure_table, list_schedules

        db = DatabaseSuite(str(tmp_path / "sch.db"))
        _ensure_table(db)
        run = _router(db)
        p = run("هر روز ساعت ۸ و نیم یادآور کن گزارش هفتگی را بفرست")
        assert p["route"] == ["scheduler"]
        assert p["result"]["registered"] is True
        assert "۸:۳۰" in p["agent_report"]
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            scheds = [s for s in list_schedules() if s.hour_of_day == 8]
        assert scheds and scheds[0].minute_of_hour == 30
        assert "و نیم" not in scheds[0].command  # stripped, only the action

    def test_quarter_hour_daily_reminder_registers(self, tmp_path: Path) -> None:
        from universal_mind.scheduler import _ensure_table, list_schedules

        db = DatabaseSuite(str(tmp_path / "sch.db"))
        _ensure_table(db)
        run = _router(db)
        p = run("هر روز ساعت ۷ و ربع یادآور کن کشکول")
        assert p["route"] == ["scheduler"]
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            scheds = [s for s in list_schedules() if s.hour_of_day == 7]
        assert scheds and scheds[0].minute_of_hour == 15

    def test_interval_reminder_registers(self, tmp_path: Path) -> None:
        from universal_mind.scheduler import _ensure_table, list_schedules

        db = DatabaseSuite(str(tmp_path / "sch.db"))
        _ensure_table(db)
        run = _router(db)
        p = run("یادآور کن هر ۳۰ دقیقه آب بخور")
        assert p["route"] == ["scheduler"]
        assert "۳۰ دقیقه" in p["agent_report"]
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            scheds = [s for s in list_schedules() if s.every_minutes == 30]
        assert scheds

    def test_reminder_without_time_is_instant_toast(self, tmp_path: Path) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.scheduler import _ensure_table

        db = DatabaseSuite(str(tmp_path / "sch.db"))
        _ensure_table(db)
        run = _router(db)
        p = run("یادآور کن گزارش بده")
        assert p["route"] != ["scheduler"]  # the old notify/pdf path stays

    def test_clock_form_0830_registers_too(self, tmp_path: Path) -> None:
        from universal_mind.scheduler import _ensure_table, list_schedules

        db = DatabaseSuite(str(tmp_path / "sch.db"))
        _ensure_table(db)
        run = _router(db)
        p = run("هر روز ساعت 8:30 یادآور کن آب")
        assert p["route"] == ["scheduler"]
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            scheds = [s for s in list_schedules() if s.hour_of_day == 8]
        assert scheds and scheds[0].minute_of_hour == 30


class TestChatMemory:
    def test_replays_the_real_conversation(self, tmp_path: Path) -> None:
        db = DatabaseSuite(str(tmp_path / "ch.db"))
        run = _router(db)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.chat_history_store import log_message

            log_message("من", "نمودار فروش را بکش", ok=True)
            log_message("سیستم", "نمودار ساخته شد", ok=True)
        p = run("آخرین گفتگویمان چه بود؟")
        assert p["route"] == ["reflexive"]
        rep = p["agent_report"]
        assert "نمودار فروش را بکش" in rep and "نمودار ساخته شد" in rep
        assert "۲ پیام" in rep

    def test_empty_history_says_so(self, tmp_path: Path) -> None:
        db = DatabaseSuite(str(tmp_path / "ch.db"))
        run = _router(db)
        p = run("آخرین گفتگویمان چه بود؟")
        assert p["route"] == ["reflexive"]
        assert "ثبت نشده" in p["agent_report"]


class TestRedTeamTimeHostility:
    def test_the_whole_corpus_stays_honest(self) -> None:
        from universal_mind.red_team import run_red_team

        from universal_mind.red_team import HOSTILE_CORPUS

        r = run_red_team()
        # THE CORPUS-SIZE LAW: never pin a magic number — an expanded corpus
        # (R57 took it from 14 to 32) must not redden a test that only meant
        # "the whole corpus stays honest". The invariant is total==len(corpus).
        assert r["total"] == len(HOSTILE_CORPUS)
        assert r["honest"] == r["total"]
        assert not r["findings"]

    def test_impossible_hour_never_wraps(self) -> None:
        from universal_mind.scheduler import parse_schedule

        assert parse_schedule("هر روز ساعت ۹۹ یادآور کن") is None
