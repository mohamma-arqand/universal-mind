"""Tests: the warmup + self-inspection passes of the tick."""

from __future__ import annotations


class TestTickWarmupAndSelfInspect:
    def test_the_warmup_pass_names_itself(self, capsys: object) -> None:
        """The warmup prints its success/failure — never silently skipped."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick  # noqa: F401 — importing proves wiring

        from unittest.mock import patch as mock_patch

        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        ctx = mock_patch.object(sched_mod, "_store", lambda: suite)
        _real_db = DatabaseSuite  # grabbed BEFORE the class-lambda patch
        with ctx, mock_patch("universal_mind.real_notify.NotifyTool.notify"), mock_patch("universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite), mock_patch.object(_real_db, "shared_persistent", classmethod(lambda cls: suite)), mock_patch("universal_mind.run_history.ChainAdvisor.advise_semantic") as warm:
            tick()
        warm.assert_called()  # the advisor was pre-warmed for the day

    def test_self_inspection_surfaces_never_started_goals(self, capsys: object) -> None:
        from unittest.mock import patch as mock_patch
        """A registered-but-never-started goal is NAMED by the tick's
        self-inspection (the agent examines itself; it does not silently
        auto-resume — the operator decides)."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        import universal_mind.agent_loop as agent_mod
        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        ctx = mock_patch.object(sched_mod, "_store", lambda: suite)
        _real_db = DatabaseSuite  # grabbed BEFORE the class-lambda patch
        with ctx, mock_patch.object(agent_mod, "_store", lambda: suite), mock_patch("universal_mind.real_notify.NotifyTool.notify"), mock_patch("universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite), mock_patch.object(_real_db, "shared_persistent", classmethod(lambda cls: suite)):
            agent_mod.start_goal("هدف: هرگز شروع نشده", ("گامیک",))
            tick()
        # the goal stayed active-never-started (auto-resume is OFF by design)
        q = suite.query("SELECT state FROM goals WHERE goal = 'هدف: هرگز شروع نشده'")
        assert q["rows"] and q["rows"][0]["state"] == "active"
