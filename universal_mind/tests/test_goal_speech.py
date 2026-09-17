"""Tests: the agent speaks — the goal's own report becomes the spoken text."""

from __future__ import annotations


class TestGoalSpeechFlow:
    def test_the_last_goal_step_is_the_spoken_text(self) -> None:
        """With a goal in the store and a goal-marked command, the speech flow
        renders the last step's verdict as the REAL Persian text to say."""
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        import universal_mind.agent_loop as agent_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        ctx: AbstractContextManager[object] = mock_patch.object(
            agent_mod, "_store", lambda: suite
        )
        with ctx:
            started = agent_mod.start_goal(
                "هدف: آزمون صوتی", ("میانگین 4 و 6 را حساب کن",)
            )
            agent_mod.run_goal(started["goal_id"])

        from universal_mind.orchestration import _flow_params

        params, flow = _flow_params(
            "speech", {}, "data", {"ok": True, "mean": 5.0}, "هدف را بلند بخوان", (),
        )
        assert flow is not None and "goal → speech" in flow
        assert "گام" in params["text"] and "داوری" in params["text"]

    def test_non_goal_commands_get_the_chain_summary_as_before(self) -> None:
        """Without the goal marker, the speech flow behaves exactly as before."""
        from universal_mind.orchestration import _flow_params

        params, flow = _flow_params(
            "speech", {}, "data", {"ok": True, "mean": 5.0}, "بلند بخوان", (),
        )
        assert flow is not None
        assert "شاخص" in params["text"] or "میانگین" in params["text"]

    def test_speech_of_a_goal_is_honest_without_a_persian_voice(self) -> None:
        """The SAPI contract unchanged: Persian text without a Persian voice
        fails with the exact remedy — never a silent fake (regression guard)."""
        from universal_mind.speech_tool import SpeechTool

        result = SpeechTool().speak("گزارش آماده است")
        if result["ok"] is False:
            assert "صدای فارسی" in result["error"]
        else:
            assert result["spoken"] is True
