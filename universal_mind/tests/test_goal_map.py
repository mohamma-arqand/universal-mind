"""Tests: the goal MAP — a real DAG with dependencies and the join step."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import patch as mock_patch

import universal_mind.agent_loop as agent_mod


def _isolated() -> AbstractContextManager[object]:
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(agent_mod, "_store", lambda: suite)


class TestParseGoalMap:
    def test_dependency_and_join_are_parsed(self) -> None:
        from universal_mind.goal_map import parse_goal_map

        gm = parse_goal_map(
            "هدف: X",
            ("محاسبه کن", "نمودار بعد از گام 1", "گزارش بعد از همه"),
        )
        assert gm is not None
        assert gm.depends_on == {1: (0,)}
        assert gm.join_index == 2

    def test_a_cycle_is_refused_never_reordered(self) -> None:
        from universal_mind.goal_map import parse_goal_map

        assert parse_goal_map("هدف: Y", ("الف بعد از گام 2", "ب بعد از گام 1")) is None

    def test_two_joins_are_refused(self) -> None:
        from universal_mind.goal_map import parse_goal_map

        assert parse_goal_map("هدف: Z", ("الف بعد از همه", "ب بعد از همه")) is None

    def test_plain_steps_have_no_map(self) -> None:
        from universal_mind.goal_map import parse_goal_map

        gm = parse_goal_map("هدف: W", ("الف", "ب"))
        assert gm is not None and gm.join_index is None and not gm.depends_on


class TestWaveExecution:
    def test_the_join_runs_last_after_every_step_ended(self) -> None:
        """The DAG goal: chart waits for compute; the JOIN (report) runs after
        every other step — even when a mid-step FAILS (ended = failure counts;
        the join still unifies the outcome)."""
        with _isolated():
            started = agent_mod.start_goal(
                "هدف: میانگین ۱۰ و ۲۰ را حساب کن و نمودارش کن بعد از گام 1 و گزارش کامل بساز بعد از همه",
                ("میانگین 10 و 20 را حساب کن", "نمودارش کن", "گزارش کامل بساز"),
                (False, False, False),
            )
            result = agent_mod.run_goal(started["goal_id"])
        assert result.finished is True
        order = [s.index for s in result.steps]
        assert order.index(2) > order.index(0)  # the join came after compute
        assert order.index(2) > order.index(1)  # and after the chart

    def test_the_map_survives_a_failing_dependency(self) -> None:
        """A failed dependency still ENDS its branch: the join runs with the
        failure honestly recorded (never silently dropped)."""
        with _isolated():
            started = agent_mod.start_goal(
                "هدف: این فرمان بیخاصیت XYZQ است بعد از گام 2 و گام 1 پایانی",
                ("این فرمان بیخاصیت XYZQ است", "گام پایانی بعد از همه"),
                (False, False),
            )
            result = agent_mod.run_goal(started["goal_id"])
        # the broken step failed; the join recorded its own outcome after it
        assert any(not s.ok for s in result.steps)
        assert any(s.index == 1 for s in result.steps)  # the join ran
