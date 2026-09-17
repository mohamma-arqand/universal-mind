"""Tests: scheduled goals — the agent inside the proactive routine."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.scheduler as sched_mod


def _isolated() -> AbstractContextManager[object]:
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(sched_mod, "_store", lambda: suite)


class TestScheduledGoals:
    def test_a_goal_with_a_schedule_clause_registers_as_one(self) -> None:
        """«هر روز ساعت ۸ هدف: ...» — one sentence, both layers, one record."""
        from universal_mind.scheduler import list_schedules, register

        with _isolated():
            result = register(
                "هر روز ساعت ۸ هدف: میانگین ۱۰ و ۲۰ را حساب کن و گزارش کامل بساز"
            )
            assert result["ok"] is True
            assert result["scheduled_goal"] is True
            assert result["steps"] == ["میانگین 10 و 20 را حساب کن", "گزارش کامل بساز"]
            assert result["hour_of_day"] == 8
            schedules = list_schedules()
            assert schedules and schedules[0].command.startswith("__goal__")

    def test_a_fired_scheduled_goal_really_runs_the_steps(self) -> None:
        """The tick fires the scheduled goal and the agent completes it."""
        from universal_mind.scheduler import register, run_due

        with _isolated():
            register("هر ۱۵ دقیقه هدف: میانگین ۴ و ۶ را حساب کن")
            with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
                fired = run_due(max_runs=2)
            assert fired["count"] >= 1
            entry = fired["fired"][0]
            assert entry["ok"] is True  # the goal FINISHED
            assert entry["route"] == ["goal"]

    def test_a_goal_without_a_schedule_gets_the_honest_template(self) -> None:
        from universal_mind.scheduler import register

        with _isolated():
            result = register("هدف: چیزی را هر از گاهی انجام بده")
            assert result["ok"] is False
            assert "بند زمان ندارد" in result["error"]

    def test_ordinary_schedules_are_untouched(self) -> None:
        """A normal scheduled command never becomes a goal."""
        from universal_mind.scheduler import list_schedules, register

        with _isolated():
            result = register("هر ۱۵ دقیقه میانگین ۲ و ۴ را حساب کن")
            assert result["ok"] is True
            assert result.get("scheduled_goal") is None
            schedules = list_schedules()
            assert not schedules[0].command.startswith("__goal__")
