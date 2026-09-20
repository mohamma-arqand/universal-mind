"""Tests: the goal parser + the agent loop — objectives become judged steps."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.agent_loop as agent_mod
from universal_mind.goal_parser import parse_goal


def _isolated() -> AbstractContextManager[object]:
    """A fresh temp goals table per test (the operator's real goals are theirs)."""
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(agent_mod, "_store", lambda: suite)


class TestGoalParser:
    def test_numeric_conjunction_is_not_split(self) -> None:
        """«۱۰ و ۲۰» is ONE data list, not two steps."""
        goal = parse_goal("هدف: میانگین ۱۰ و ۲۰ را حساب کن و نمودارش کن")
        assert goal is not None
        assert goal.steps == ("میانگین 10 و 20 را حساب کن", "نمودارش کن")

    def test_sobt_separator(self) -> None:
        goal = parse_goal("هدف: تحلیل کن سپس گزارش بساز")
        assert goal is not None
        assert goal.steps == ("تحلیل کن", "گزارش بساز")

    def test_hadafem_form(self) -> None:
        goal = parse_goal("هدفم تحلیل فروش ماهانه است")
        assert goal is not None
        assert goal.steps == ("تحلیل فروش ماهانه",)

    def test_non_goal_is_none_never_hijacked(self) -> None:
        """An ordinary command is NOT a goal — the agent never takes over."""
        assert parse_goal("میانگین ۲ و ۴ را حساب کن") is None

    def test_empty_body_refused(self) -> None:
        assert parse_goal("هدف:") is None


class TestAgentLoop:
    def test_a_real_goal_runs_step_by_step(self) -> None:
        """Every step really runs through the engine with its ARETĒ verdict."""
        from universal_mind.agent_loop import goal_run_report, run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: میانگین ۴ و ۶ را حساب کن و نمودارش کن",
                ("میانگین 4 و 6 را حساب کن", "نمودارش کن"),
            )
            assert started["ok"] is True
            result = run_goal(started["goal_id"])
            assert result.finished is True
            assert len(result.steps) == 2
            assert all(s.ok for s in result.steps)
            assert all(s.excellence >= 0.5 for s in result.steps)  # judged
            report = goal_run_report(result)
            assert "🎯" in report and "داوری" in report

    def test_a_failing_step_stops_the_goal_honestly(self) -> None:
        """A broken step stops the run at THAT step — never a blind march."""
        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: نامفهوم",
                ("zzqx بیقابلیت zzqx", "نمودارش کن"),
            )
            result = run_goal(started["goal_id"])
            assert result.finished is False
            assert result.stopped_at == 0  # stopped at the first step
            assert "توقف" in result.reasoning or "شکست" in result.reasoning

    def test_the_same_goal_resumes_not_duplicates(self) -> None:
        """Starting an identical active goal REVIVES it (one goal, one record)."""
        from universal_mind.agent_loop import start_goal

        with _isolated():
            first = start_goal("هدف: آزمون", ("گامیک",))
            second = start_goal("هدف: آزمون", ("گامیک",))
            assert first["goal_id"] == second["goal_id"]
            assert second["resumed"] is True

    def test_outcomes_are_persisted_for_audit(self) -> None:
        """The goal's outcome history is in the db, not just in memory."""
        import json

        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated():
            started = start_goal(
                "هدف: میانگین ۳ را حساب کن", ("میانگین 3 را حساب کن",)
            )
            run_goal(started["goal_id"])

            db = agent_mod._store()
            q = db.query("SELECT outcomes, state FROM goals WHERE id = ?",
                         (str(started["goal_id"]),))
            outcomes = json.loads(q["rows"][0]["outcomes"])
            assert len(outcomes) == 1
            assert q["rows"][0]["state"] == "done"
