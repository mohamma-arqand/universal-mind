"""Tests: the scheduler — the platform runs itself on the operator's clock."""

from __future__ import annotations

from datetime import datetime, timedelta

from universal_mind.scheduler import (
    Schedule,
    _next_due,
    due_schedules,
    list_schedules,
    mark_run,
    parse_schedule,
    register,
    run_due,
)


class TestParseSchedule:
    def test_daily_at_eight(self) -> None:
        assert parse_schedule("هر روز ساعت ۸ گزارش کامل بده") == {
            "every_minutes": 1440, "hour_of_day": 8,
        }

    def test_every_n_minutes_with_persian_digits(self) -> None:
        assert parse_schedule("هر ۳۰ دقیقه میانگین بگیر") == {
            "every_minutes": 30, "hour_of_day": -1,
        }

    def test_every_n_hours(self) -> None:
        assert parse_schedule("هر ۲ ساعت نمودار بکش") == {
            "every_minutes": 120, "hour_of_day": -1,
        }

    def test_unrecognized_is_none_never_a_guess(self) -> None:
        assert parse_schedule("sometime maybe") is None


class TestRegisterAndDue:
    def test_register_strips_the_schedule_clause(self) -> None:
        result = register("هر ۱۵ دقیقه میانگین ۱ و ۲ را حساب کن")
        assert result["ok"] is True
        assert result["command"] == "میانگین ۱ و ۲ را حساب کن"  # action only
        assert result["every_minutes"] == 15

    def test_bad_syntax_gets_the_honest_template(self) -> None:
        result = register("یکی یه وقتایی گزارش بده")
        assert result["ok"] is False
        assert "قالب درست" in result["error"]

    def test_never_run_is_due_immediately(self) -> None:
        sched = Schedule(1, "cmd", 30, -1, last_run="", active=True)
        now = datetime(2026, 9, 16, 12, 0)
        assert _next_due(sched, now) == now

    def test_interval_schedule_due_after_interval(self) -> None:
        now = datetime(2026, 9, 16, 12, 0)
        past = now - timedelta(minutes=29)  # 11:31 → next due 12:01 (not yet)
        sched = Schedule(1, "cmd", 30, -1, last_run=past.isoformat(), active=True)
        assert _next_due(sched, now) == past + timedelta(minutes=30)  # in 1 min
        # a schedule whose last_run was long ago IS due now
        old_run = (now - timedelta(minutes=45)).isoformat()
        sched_old = Schedule(2, "cmd", 30, -1, last_run=old_run, active=True)
        due_at = _next_due(sched_old, now)
        assert due_at is not None and due_at <= now

    def test_daily_schedule_rolls_to_tomorrow_when_already_run(self) -> None:
        now = datetime(2026, 9, 16, 9, 0)
        ran_today = datetime(2026, 9, 16, 8, 0).isoformat()
        sched = Schedule(1, "cmd", 1440, 8, last_run=ran_today, active=True)
        assert _next_due(sched, now) == datetime(2026, 9, 17, 8, 0)

    def test_inactive_is_never_due(self) -> None:
        sched = Schedule(1, "cmd", 30, -1, last_run="", active=False)
        assert _next_due(sched, datetime(2026, 9, 16)) is None


class TestRunDue:
    def test_run_due_fires_and_advances_the_clock(self) -> None:
        """A fresh never-run schedule really fires and records last_run."""
        import uuid

        suffix = uuid.uuid4().hex[:6]
        action = f"میانگین ۳ و ۷ {suffix}"
        result = register(f"هر ۱۵ دقیقه {action} را حساب کن")
        assert result["ok"] is True
        # the fresh registration is never-run → due immediately
        fresh = [s for s in list_schedules() if suffix in s.command and s.last_run == ""]
        assert fresh, "the new schedule must exist un-fired"
        fired = run_due(max_runs=5)
        assert fired["count"] >= 1
        after = {s.schedule_id: s.last_run for s in list_schedules()}
        assert any(after.get(s.schedule_id) for s in fresh)  # it really fired

    def test_second_run_after_marking_is_not_due(self) -> None:
        """Immediately after firing, the schedule is NOT due again (interval)."""
        due_now = due_schedules()
        for s in due_now:
            mark_run(s.schedule_id)
        # interval schedules need their interval to pass; daily ones need a day
        still_due = [
            s for s in due_schedules()
            if s.every_minutes > 1  # ignore pathological one-minute schedules
        ]
        assert still_due == []


class TestSchedulerCLI:
    def test_cli_register_and_list_and_run(self, capsys: object) -> None:
        """The CLI triad works end to end (isolated temp store — the CLI must
        not fire the operator's real schedules as a side effect of testing)."""
        from unittest.mock import patch as mock_patch

        from universal_mind.cli import main
        from universal_mind.database_suite import DatabaseSuite
        import universal_mind.scheduler as sched_mod

        suite = DatabaseSuite()
        with mock_patch.object(sched_mod, "_store", lambda: suite):
            rc = main(["schedule", "هر ۹۹ دقیقه میانگین ۵ و ۹ را حساب کن"])
            assert rc == 0
            rc = main(["schedule-list"])
            assert rc == 0
            rc = main(["schedule-run"])
            assert rc == 0

    def test_cli_bad_schedule_fails_with_template(self, capsys: object) -> None:
        from universal_mind.cli import main

        rc = main(["schedule", "یه وقتایی شاید"])
        assert rc == 1  # honest failure, never a guessed schedule
