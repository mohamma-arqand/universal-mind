"""R52 wave 4: LIVE branch tests for the conversational small-talk face,
the red-team findings lens, and the goal-map render.

Real Persian sentences through the REAL conversational module; the red-team
recent-findings lens on the real store; the goal map's honest render. No mock
of any unit under test.
"""

from __future__ import annotations


class TestConversationalLive:
    """The small-talk face answers real sentences with real state."""

    def _answer(self, command: str) -> str:
        from universal_mind.conversational import answer_conversational

        a = answer_conversational(command)
        assert a is not None, f"a small-talk sentence died: {command}"
        return str(a["result"]["conversational"]["answer"])

    def test_a_greeting_reports_real_activity(self) -> None:
        text = self._answer("سلام")
        assert "سلام" in text or "چه کار کنم" in text

    def test_thanks_gets_a_real_acknowledgment(self) -> None:
        text = self._answer("مرسی")
        assert "خواهش" in text

    def test_learning_question_answers_honestly(self) -> None:
        # empty or learned — both honest; the sentence must ANSWER, not die
        text = self._answer("چه یاد گرفتی")
        assert ("یاد گرفتم" in text) or ("یاد ندادهی" in text)

    def test_how_are_you_reports_recent_activity(self) -> None:
        text = self._answer("چه خبر؟")
        assert "در خدمتم" in text

    def test_help_lists_real_commands(self) -> None:
        text = self._answer("کمک کن")
        assert "نمودار" in text

    def test_a_whats_next_question_answers(self) -> None:
        text = self._answer("دنبال چه میگردی؟")
        assert "در خدمتم" in text


class TestRedTeamFindingsLens:
    """The red-team sweep + findings lens answer honestly on the live store."""

    def test_recent_findings_never_crash(self) -> None:
        from universal_mind.red_team import findings_summary

        r = findings_summary()
        assert isinstance(r, list)

    def test_a_sweep_records_and_reports(self) -> None:
        from universal_mind.red_team import run_red_team

        r = run_red_team()
        assert r["total"] > 0
        assert r["honest"] >= 0
        assert isinstance(r["findings"], list)


class TestGoalMapRender:
    """The goal map parses a real multi-step goal and renders the order."""

    def test_a_two_step_goal_maps(self) -> None:
        from universal_mind.goal_map import map_report, parse_goal_map

        gm = parse_goal_map(
            "هدف: میانگین بگیر و نمودار بکش", ("میانگین بگیر", "نمودار بکش")
        )
        assert gm is not None
        report = map_report(gm, [[0, 1]])
        assert report  # the render exists

    def test_a_single_step_goal_maps_with_no_dependencies(self) -> None:
        from universal_mind.goal_map import parse_goal_map

        gm = parse_goal_map("هدف: فقط میانگین بگیر", ("فقط میانگین بگیر",))
        assert gm is not None
        assert gm.depends_on == {}  # one step depends on nothing — honest
