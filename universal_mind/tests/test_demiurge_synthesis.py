"""Tests for Demiurge result synthesis (all methods)."""

from __future__ import annotations

import pytest

from universal_mind.demiurge.strategies import StrategyResult
from universal_mind.demiurge.synthesis import (
    SynthesisError,
    synthesize_by_sub_intent,
    synthesize_results,
)


def _r(strategy_id: str, success: bool, result: object = "ok", error: str | None = None) -> StrategyResult:
    return StrategyResult(
        strategy_id=strategy_id,
        sub_intent_id="sub0",
        success=success,
        result=result,
        error=error,
    )


def test_empty_results_returns_failure() -> None:
    out = synthesize_results([])
    assert out.success is False
    assert out.merged_result is None
    assert out.confidence == 0.0


def test_first_success_picks_first_successful() -> None:
    out = synthesize_results([_r("a", False, error="e"), _r("b", True, "B"), _r("c", True, "C")])
    assert out.success is True
    assert out.merged_result == "B"
    assert out.synthesis_method == "first_success"


def test_first_success_all_failed_reports_conflict() -> None:
    out = synthesize_results([_r("a", False, error="boom")])
    assert out.success is False
    assert out.conflicts == [{"error": "boom", "sub_intent_id": "sub0"}]


def test_majority_vote_picks_majority() -> None:
    out = synthesize_results(
        [_r("a", True, "X"), _r("b", True, "X"), _r("c", True, "Y")],
        method="majority_vote",
    )
    assert out.success is True
    assert out.merged_result == "X"
    assert out.confidence == pytest.approx(2 / 3)


def test_merge_all_default_combines_to_list() -> None:
    out = synthesize_results([_r("a", True, "A"), _r("b", True, "B")], method="merge_all")
    assert out.success is True
    assert out.merged_result == ["A", "B"]


def test_merge_all_custom_fn() -> None:
    out = synthesize_results(
        [_r("a", True, 1), _r("b", True, 2)],
        method="merge_all",
        merge_fn=lambda xs: sum(xs),
    )
    assert out.merged_result == 3


def test_custom_method_requires_merge_fn() -> None:
    out = synthesize_results(
        [_r("a", True, 1)],
        method="custom",
        merge_fn=lambda rs: rs[0].result,
    )
    assert out.success is True
    assert out.merged_result == 1


def test_unknown_method_raises() -> None:
    with pytest.raises(SynthesisError):
        synthesize_results([_r("a", True)], method="bogus")


def test_synthesize_by_sub_intent() -> None:
    grouped = {
        "s0": [_r("a", True, "A0")],
        "s1": [_r("b", True, "B0")],
    }
    out = synthesize_by_sub_intent(grouped)
    assert set(out) == {"s0", "s1"}
    assert out["s0"].merged_result == "A0"
    assert out["s1"].merged_result == "B0"