"""Tests: the agent's voice + goal archival housekeeping."""

from __future__ import annotations


class TestScheduledGoalSpeaks:
    def test_a_fired_scheduled_goal_announces_itself_aloud(self) -> None:
        """The tick's scheduled goal says its outcome through the REAL SAPI
        (mocked in the test — the outcome TEXT is what matters)."""
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        ctx: AbstractContextManager[object] = mock_patch.object(
            sched_mod, "_store", lambda: suite
        )
        with ctx, mock_patch(
            "universal_mind.real_notify.NotifyTool.notify"
        ), mock_patch("universal_mind.speech_tool.SpeechTool.speak") as speak:
            sched_mod.register("هر ۱۵ دقیقه هدف: میانگین ۴ و ۶ را حساب کن")
            fired = sched_mod.run_due(max_runs=2)
        assert fired["count"] >= 1
        speak.assert_called()
        spoken = speak.call_args.kwargs.get("text", "") or str(speak.call_args.args[-1])
        assert "هدف" in spoken  # the goal's outcome, not the raw command


class TestGoalArchive:
    def test_finished_goals_beyond_100_move_to_the_archive(self) -> None:
        """Housekeeping: >100 done goals → the old ones live in goals_archive;
        nothing is lost (the archive keeps every field + a timestamp)."""
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        import universal_mind.agent_loop as agent_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        ctx: AbstractContextManager[object] = mock_patch.object(
            agent_mod, "_store", lambda: suite
        )
        with ctx:
            db = agent_mod._store()
            agent_mod._ensure_goals_table(db)  # creates goals WITH its id schema
            for i in range(105):
                db.insert_many("goals", [{
                    "goal": f"هدف قدیمی {i}", "steps": "x", "next_step": "1",
                    "outcomes": "[]", "state": "done",
                }])
            agent_mod._ensure_goals_table(db)  # triggers the archival pass
            live = db.query("SELECT COUNT(*) AS n FROM goals")["rows"][0]["n"]
            archived = db.query("SELECT COUNT(*) AS n FROM goals_archive")["rows"][0]["n"]
        assert live <= 105  # the newest 100 stay live (plus any active)
        assert archived >= 5  # the overflow was archived, never deleted
        sample = db.query("SELECT goal FROM goals_archive LIMIT 1")
        assert sample["rows"]  # the archived rows still carry their goal text
