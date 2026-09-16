"""Tests: planner learning — the needs table earns its entries from verdicts."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch as mock_patch

import universal_mind.planner_learning as pl
from universal_mind.planner_learning import (
    best_learned_operation,
    learned_operations,
    lessons_report,
    teach,
)


def _isolated_planner_learning() -> Any:
    """Route every store call to ONE fresh temp DatabaseSuite (a single
    instance per context — a lambda would build a NEW temp db per call and
    writes would never be seen by reads)."""
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(pl, "_store", lambda: suite)


class TestTeach:
    def test_success_teaches_failure_never_does(self) -> None:
        with _isolated_planner_learning():
            teach("cap", "good_op", 1.0, True)
            teach("cap", "failed_op", 0.9, False)
            ops = {l.operation for l in learned_operations("cap")}
        assert ops == {"good_op"}  # the failure taught nothing

    def test_no_excellence_teaches_nothing(self) -> None:
        with _isolated_planner_learning():
            teach("cap", "op", None, True)  # type: ignore[arg-type]
            assert learned_operations("cap") == []


class TestBestLearned:
    def test_best_meets_the_bar_first(self) -> None:
        with _isolated_planner_learning():
            teach("cap", "weak", 0.5, True)
            teach("cap", "strong", 0.9, True)
            best = best_learned_operation("cap")
            assert best is not None
            assert best.operation == "strong"
            assert abs(best.mean_excellence - 0.9) < 1e-9

    def test_all_below_bar_is_none(self) -> None:
        with _isolated_planner_learning():
            teach("cap", "weak", 0.5, True)
            assert best_learned_operation("cap") is None

    def test_unknown_capability_is_none(self) -> None:
        with _isolated_planner_learning():
            assert best_learned_operation("never-seen") is None


class TestPlannerUsesLearning:
    def test_a_silent_operation_is_chosen_from_history(self) -> None:
        """When the sentence is silent, the PROVEN operation wins over the
        static default (learning displaces the constant table)."""
        from universal_mind.dependency_planner import plan_chain

        with _isolated_planner_learning():
            # teach a proven operation for the data capability
            lesson_op = "variance"
            with mock_patch.object(
                pl, "best_learned_operation",
                lambda cap, bar=0.75: pl.OperationLesson(
                    capability=cap, operation=lesson_op, mean_excellence=0.95, uses=4,
                ) if cap == "data" else None,
            ):
                plan = plan_chain(["data", "database"])
                data_step = [s for s in plan.steps if s.capability == "data"][0]
                assert data_step.operation == "variance"
                assert "تاریخچه" in data_step.reason

    def test_explicit_intent_beats_learning(self) -> None:
        from universal_mind.dependency_planner import plan_chain

        plan = plan_chain(["data"], {"data": {"operation": "stats"}})
        data_step = [s for s in plan.steps if s.capability == "data"][0]
        assert data_step.operation == "stats"  # the sentence wins, always

    def test_pdf_and_image_keep_synthesis_priority(self) -> None:
        """The learned lens must NOT displace the synthesis-aware choice for
        pdf/image — the chain's own flows outrank history."""
        from universal_mind.dependency_planner import plan_chain

        with mock_patch.object(
            pl, "best_learned_operation",
            lambda cap, bar=0.75: pl.OperationLesson(
                capability=cap, operation="document", mean_excellence=0.95, uses=9,
            ),
        ):
            plan = plan_chain(["chart", "pdf"])
            pdf_step = [s for s in plan.steps if s.capability == "pdf"][0]
            assert pdf_step.operation == "persian_report"  # synthesis beats history


class TestReport:
    def test_lessons_report_shape(self) -> None:
        with _isolated_planner_learning():
            teach("capA", "op1", 0.8, True)
            report = lessons_report()
            assert any(
            r["capability"] == "capA" and r["operation"] == "op1"
                for r in report["lessons"]
            )
