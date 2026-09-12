"""Tests for counterfactual reasoning — does the judgment survive a reversed premise?"""

from __future__ import annotations

from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
from universal_mind.arete.counterfactual import (
    CounterfactualError,
    CounterfactualResult,
    counterfactual_check,
)
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float, courage: float = 1.0) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"out-{strategy_id}",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": courage, "temperance": 1.0}},
    )


def test_winner_hinging_on_wisdom_is_fragile() -> None:
    # A candidate that wins *only because* of strong wisdom collapses when that
    # premise is reversed — the decision was fragile.
    dispute = Dispute(goal="pick", candidates=[_candidate("good", 0.9), _candidate("bad", 0.3)])
    arbiter = InMemoryArbiter()
    verdict = arbiter.arbitrate(dispute)
    assert verdict.winner_strategy_id == "good"

    result = counterfactual_check(dispute, verdict, assumption="wisdom", arbiter=arbiter)
    # Reversing "good"'s wisdom (0.9 -> 0.1) drops it below "bad", so it is fragile.
    assert result.robust is False
    assert result.counterfactual_winner == "bad"
    assert "fragile" in result.explanation


def test_no_original_winner_is_reported() -> None:
    # A tied dispute defers; there is no winner, and the counterfactual is
    # defined accordingly.
    dispute = Dispute(goal="pick", candidates=[_candidate("a", 0.5), _candidate("b", 0.5)])
    verdict = InMemoryArbiter().arbitrate(dispute)
    assert verdict.winner_strategy_id is None
    result = counterfactual_check(dispute, verdict)
    assert result.original_winner is None
    assert result.robust is False


def test_empty_dispute_raises() -> None:
    dispute = Dispute(goal="pick", candidates=[])
    verdict = InMemoryArbiter().arbitrate(dispute)  # DENY, empty
    try:
        counterfactual_check(dispute, verdict)
        raised = False
    except CounterfactualError:
        raised = True
    assert raised is True


def test_result_is_frozen_dataclass() -> None:
    from dataclasses import FrozenInstanceError

    dispute = Dispute(goal="pick", candidates=[_candidate("x", 0.8)])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = counterfactual_check(dispute, verdict)
    assert isinstance(result, CounterfactualResult)
    try:
        result.robust = True  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_reversed_value_is_flipped() -> None:
    import math

    dispute = Dispute(goal="pick", candidates=[_candidate("x", 0.8)])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = counterfactual_check(dispute, verdict, assumption="wisdom")
    assert result.original_value == 0.8
    assert math.isclose(result.reversed_value, 0.2)


def test_undeclared_dimension_default_matches_reversal() -> None:
    """An assumption the candidate never declared must report the same default the
    reversal actually used (0.5), not invent original=0.0 / reversed=1.0 — the
    reported values must reflect the flip that happened, not a phantom premise."""
    import math

    candidate = CandidateOutput(
        strategy_id="x",
        output="out-x",
        # "wisdom" is absent from virtues entirely.
        metadata={"virtues": {"justice": 1.0, "courage": 1.0, "temperance": 1.0}},
    )
    dispute = Dispute(goal="pick", candidates=[candidate])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = counterfactual_check(dispute, verdict, assumption="wisdom")
    # Once wisdom is undeclared, _reverse_candidate flips 0.5 -> 0.5 (no-op).
    assert math.isclose(result.original_value, 0.5)
    assert math.isclose(result.reversed_value, 0.5)