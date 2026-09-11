"""Tests for cross-model judging — a second foreign judge adjudicates the first."""

from __future__ import annotations

from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
from universal_mind.arete.cross_judge import CrossJudgeResult, cross_judge
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float, courage: float = 1.0) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"out-{strategy_id}",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": courage, "temperance": 1.0}},
    )


def test_two_rubrics_agree_on_clear_winner() -> None:
    dispute = Dispute(goal="pick", candidates=[_candidate("good", 0.95), _candidate("bad", 0.2)])
    primary = InMemoryArbiter().arbitrate(dispute)
    result = cross_judge(dispute, primary)
    assert result.aligned is True
    assert result.confidence == 1.0
    assert result.primary_winner == "good" and result.second_winner == "good"


def test_courage_gate_makes_second_judge_diverge() -> None:
    # A candidate strong on wisdom but low on courage: the primary (justice-only
    # hard gate) accepts it, but the foreign rubric (justice + courage) rejects.
    dispute = Dispute(goal="pick", candidates=[_candidate("coward", 0.8, courage=0.1)])
    primary = InMemoryArbiter().arbitrate(dispute)
    result = cross_judge(dispute, primary)
    # The foreign gate must diverge: low courage -> second judge denies.
    assert result.aligned is False
    assert "diverge" in result.explanation


def test_both_decline_is_inconclusive_not_contradictory() -> None:
    dispute = Dispute(goal="pick", candidates=[_candidate("a", 0.3), _candidate("b", 0.3)])
    primary = InMemoryArbiter().arbitrate(dispute)
    assert primary.winner_strategy_id is None
    result = cross_judge(dispute, primary)
    assert result.primary_winner is None
    assert result.confidence == 0.5


def test_result_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = CrossJudgeResult("x", "x", True, "allow", "allow", 1.0, "ok")
    try:
        r.confidence = 0.0  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True