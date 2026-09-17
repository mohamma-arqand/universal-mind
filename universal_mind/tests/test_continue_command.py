"""Tests: «ادامه بده» — the shortest resume, honest in every state."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.agent_loop as agent_mod


def _isolated_goals() -> AbstractContextManager[object]:
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    ctxs = [
        mock_patch.object(agent_mod, "_store", lambda: suite),
        # the router's resume path opens its own DatabaseSuite(persistent=True)
        # — patch the goals-table read to use the same isolated suite.
    ]
    from contextlib import ExitStack

    stack = ExitStack()
    for c in ctxs:
        stack.enter_context(c)
    return stack


class TestContinueCommand:
    def test_no_stopped_goals_is_honest_silence(self) -> None:
        """With nothing stopped, «ادامه بده» says so — never invents work."""
        from universal_mind.persian_router import route_and_run

        with _isolated_goals(), mock_patch(
            "universal_mind.database_suite.DatabaseSuite.DEFAULT_DB_DIR",
            _temp_default_dir(),
        ):
            payload = route_and_run("ادامه بده")
        assert payload["ok"] is True
        assert "هدفی متوقف نشده" in payload["agent_report"]

    def test_a_stopped_goal_resumes_from_its_failing_step(self) -> None:
        """The stopped goal re-runs ONLY the failed step (step 1's success is
        never re-executed — its outcome stays single in the ledger)."""
        import json

        from universal_mind.agent_loop import run_goal, start_goal

        with _isolated_goals():
            started = start_goal(
                "هدف: آزمون ادامه", ("میانگین 4 و 6 را حساب کن", "این فرمان هیچ قابلیتی ندارد XYZQ")
            )
            first = run_goal(started["goal_id"])
            assert first.finished is False and first.stopped_at == 1
            resumed = run_goal(started["goal_id"])  # what «ادامه بده» calls
            db = agent_mod._store()
            q = db.query("SELECT outcomes FROM goals WHERE id = ?", (str(started["goal_id"]),))
            outcomes = json.loads(q["rows"][0]["outcomes"])
        # step 0 ran ONCE total; step 1 was attempted twice (both failed)
        step0 = [o for o in outcomes if o["index"] == 0]
        step1 = [o for o in outcomes if o["index"] == 1]
        assert len(step0) == 1 and len(step1) == 2
        assert resumed.finished is False  # the broken step honestly failed again

    def test_resume_wording_routes_as_a_goal(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated_goals():
            payload = route_and_run("ادامه بده")
        assert payload["route"] == ["goal"]


def _temp_default_dir() -> object:
    import tempfile
    from pathlib import Path

    return Path(tempfile.mkdtemp(prefix="um-continue-test-"))
