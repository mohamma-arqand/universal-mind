"""Tests: «وضعیت» — the agent's status board, honest in every state."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.agent_loop as agent_mod


def _isolated() -> AbstractContextManager[object]:
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(agent_mod, "_store", lambda: suite)


class TestStatusCommand:
    def test_no_goals_is_the_honest_empty(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated(), mock_patch(
            "universal_mind.database_suite.DatabaseSuite.DEFAULT_DB_DIR", _temp_dir()
        ):
            payload = route_and_run("وضعیت")
        assert payload["ok"] is True
        assert "هدفی ثبت نشده" in payload["agent_report"]

    def test_status_wordings_route_as_goal(self) -> None:
        from universal_mind.persian_router import route_and_run

        for phrase in ("وضعیت", "وضعیت عامل", "چه خبر"):
            payload = route_and_run(phrase)
            assert payload["route"] == ["goal"]

    def test_status_lists_goals_with_verdicts(self) -> None:
        """A done goal appears as ✅ with its last verdict; a stopped one ⏸.

        Both the goal store AND the status read must see the SAME isolated
        suite (the status path opens its own DatabaseSuite — patched here)."""
        from universal_mind.agent_loop import run_goal, start_goal
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        import universal_mind.database_suite as ds_mod

        with _isolated(), mock_patch.object(
            ds_mod, "DatabaseSuite", lambda persistent=True, **kw: suite
        ), mock_patch.object(
            agent_mod, "_store", lambda: suite
        ):
            done = start_goal("هدف: نمونه تمام", ("میانگین 4 و 6 را حساب کن",))
            run_goal(done["goal_id"])
            stopped = start_goal(
                "هدف: نمونه متوقف", ("این فرمان بیخاصیت XYZQ را اجرا کن",)
            )
            run_goal(stopped["goal_id"])

            from universal_mind.persian_router import route_and_run

            payload = route_and_run("وضعیت")
        report = payload["agent_report"]
        assert "نمونه تمام" in report and "✅" in report
        assert "نمونه متوقف" in report and "⏸" in report
        assert "۱.۰" in report  # the done goal's verdict in Persian digits


def _temp_dir() -> object:
    import tempfile
    from pathlib import Path

    return Path(tempfile.mkdtemp(prefix="um-status-test-"))
