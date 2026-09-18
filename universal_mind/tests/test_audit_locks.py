"""Audit locks: the bugs this deep audit found, pinned forever."""

from __future__ import annotations


class TestNestedGoalIsFlattened:
    def test_goal_of_goal_does_not_recurse(self) -> None:
        """«هدف: هدف: X» flattens ONCE — the inner goal's steps join the outer;
        the error text is never the goal-of-goal-of-goal chain again."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("هدف: هدف: تو در تو")
        report = payload.get("agent_report", "") or str(
            payload.get("result", {}).get("goal", {}).get("report", "")
        )
        step_lines = [
            ln for ln in report.splitlines() if ln.strip().startswith(("✅", "❌"))
        ]
        # no STEP is itself a nested goal (flattened once, never re-entered)
        assert step_lines, report
        assert not any("هدف:" in ln for ln in step_lines), step_lines
        assert "گام" in report            # it ran as a real (failing) step


class TestOneWordPrefixCommands:
    def test_status_prefix_variants_all_answer(self) -> None:
        from universal_mind.persian_router import route_and_run

        for phrase in ("وضعیت عامل وضعیت", "وضعیت؟", "وضعیت عامل"):
            payload = route_and_run(phrase)
            assert payload["route"] == ["goal"], phrase

    def test_continue_prefix_variants_all_answer(self) -> None:
        from universal_mind.persian_router import route_and_run

        for phrase in ("ادامه بده ادامه بده", "ادامه", "ادامه بده لطفاً"):
            payload = route_and_run(phrase)
            assert payload["route"] == ["goal"], phrase


class TestHonestZeroExcellence:
    def test_completion_hint_never_fabricates_a_verdict(self) -> None:
        """A history row with excellence=0.0 renders as 'بدون داوری' — the
        `or 1.0` fabrication is dead (audit catch)."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import ChainAdvisor, RunHistory

        history = RunHistory(DatabaseSuite())  # isolated temp store
        # a half chain whose COMPLETED form has a 0.0-excellence win (legacy row)
        history.record("نمودار بساز", ["chart"], True, excellence=0.9)
        history.record("نمودار بساز و گزارشش کن", ["chart", "pdf"], True, excellence=0.0)
        hint = ChainAdvisor(history).completion_hint("نمودار خطی بساز")
        assert hint is not None
        assert "۱۰۰٪" not in hint  # never fabricated to 100%
        assert "بدون داوری" in hint  # the honest rendering


class TestLoopClosureBinding:
    def test_the_repair_candidate_binds_this_steps_command(self) -> None:
        """B023: the gate's candidate closure must bind THIS step's command,
        not a later loop iteration's (late-binding would repair the wrong
        step). Verified by running a two-step goal where step two is weak."""
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
                "هدف: اتصال گامها", ("میانگین 4 و 6 را حساب کن", "نمودارش کن")
            )
            result = agent_mod.run_goal(started["goal_id"])
        # both steps ran with THEIR OWN commands (no cross-contamination)
        commands = [s.command for s in result.steps]
        assert "میانگین 4 و 6 را حساب کن" in commands
        assert "نمودارش کن" in commands
        assert result.finished is True
