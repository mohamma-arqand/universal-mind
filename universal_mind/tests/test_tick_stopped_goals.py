"""Tests: the tick surfaces STOPPED GOALS in its toast («ادامه بده» hint)."""

from __future__ import annotations


class TestTickStoppedGoals:
    def test_stopped_goals_surface_in_the_toast(self) -> None:
        """A stopped goal in the store → the tick's toast names it and the
        «ادامه بده» recovery. Mocked toast (a test never spams the desktop)."""
        import sys
        from contextlib import AbstractContextManager
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        import universal_mind.agent_loop as agent_mod
        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        store: AbstractContextManager[object] = mock_patch.object(
            sched_mod, "_store", lambda: suite
        )
        with store, mock_patch.object(
            agent_mod, "_store", lambda: suite
        ), mock_patch(
            "universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite
        ), mock_patch(
            "universal_mind.real_notify.NotifyTool.notify"
        ) as toast:
            # a goal that stops mid-way (the broken step)
            started = agent_mod.start_goal(
                "هدف: تیک تست", ("این فرمان بیخاصیت XYZQ است",)
            )
            agent_mod.run_goal(started["goal_id"])
            result = tick()
        assert result["count"] >= 0  # the tick ran fine
        body = toast.call_args.kwargs.get("body", "") if toast.call_args else ""
        assert "هدفِ متوقف‌شده" in body
        assert "ادامه بده" in body
