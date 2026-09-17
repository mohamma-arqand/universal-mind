"""Tests: conditional goal steps — «اگر X موفق بود، Y»."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.agent_loop as agent_mod


def _isolated() -> AbstractContextManager[object]:
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(agent_mod, "_store", lambda: suite)


class TestConditionalParsing:
    def test_the_guard_is_detected(self) -> None:
        from universal_mind.goal_parser import parse_goal

        goal = parse_goal("هدف: میانگین ۴ و ۶ را حساب کن و اگر موفق بود نمودارش کن")
        assert goal is not None
        assert goal.steps == ("میانگین 4 و 6 را حساب کن", "نمودارش کن")
        assert goal.guarded == (False, True)

    def test_plain_steps_have_no_guards(self) -> None:
        from universal_mind.goal_parser import parse_goal

        goal = parse_goal("هدف: الف کن و ب کن")
        assert goal is not None
        assert goal.guarded == (False, False)


class TestConditionalExecution:
    def test_failure_skips_the_guarded_step_honestly(self) -> None:
        """The previous step fails → the conditional step is SKIPPED with the
        exact reason, and the goal finishes (the guard reacted to failure)."""
        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: آزمون شرط",
                ("این فرمان بیخاصیت XYZQ را اجرا کن", "نمودارش کن"),
                (False, True),
            )
            result = run_goal(started["goal_id"])
        assert result.finished is True
        assert len(result.steps) == 2
        assert result.steps[0].ok is False          # the honest failure
        assert "ناموفق" in result.steps[1].detail   # the guard skipped, honestly

    def test_success_runs_the_guarded_step(self) -> None:
        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: آزمون شرط موفق",
                ("میانگین 4 و 6 را حساب کن", "نمودارش کن"),
                (False, True),
            )
            result = run_goal(started["goal_id"])
        assert result.finished is True
        assert result.steps[1].ok is True
        assert "رد شد" not in (result.steps[1].detail or "")  # it REALLY ran

    def test_a_failing_unconditional_step_still_stops_the_goal(self) -> None:
        """Guards did not weaken the honest stop: without a following guard,
        a failure still stops the goal at that step."""
        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: توقف",
                ("این فرمان بیخاصیت XYZQ را اجرا کن", "نمودارش کن"),
                (False, False),  # NO guard on the next step
            )
            result = run_goal(started["goal_id"])
        assert result.finished is False
        assert result.stopped_at == 0
