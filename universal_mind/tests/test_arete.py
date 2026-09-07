"""Tests for ARETĒ arbitration — non-compensatory virtue adjudication."""

from __future__ import annotations

import pytest

from universal_mind.arete import (
    Arbitrator,
    AreteError,
    CardinalVirtue,
    Dispute,
    InMemoryArbiter,
    VirtueWeights,
)
from universal_mind.powers.judgment import CandidateOutput, Verdict


def candidate(strategy_id: str, virtues: dict[str, float], output: str = "result") -> CandidateOutput:
    """Build a candidate carrying a precomputed virtue observation."""
    return CandidateOutput(
        strategy_id=strategy_id,
        output=output,
        metadata={"virtues": virtues} if virtues else {},
    )


def dispute(*cands: CandidateOutput, goal: str = "choose best") -> Dispute:
    """Build a dispute over the given candidates."""
    return Dispute(goal=goal, candidates=list(cands))


def perfect() -> dict[str, float]:
    """A virtue observation that satisfies every gate perfectly."""
    return {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 1.0}


def test_no_candidates_denies() -> None:
    """An empty field can never be ratified."""
    verdict = InMemoryArbiter().arbitrate(dispute(goal="anything"))
    assert verdict.decision is Verdict.DENY
    assert verdict.winner_strategy_id is None


def test_accepts_excellent_candidate() -> None:
    """A fully virtuous candidate is ratified as the single winner."""
    cands = [candidate("A", perfect())]
    verdict = InMemoryArbiter().arbitrate(dispute(*cands))
    assert verdict.decision is Verdict.ALLOW
    assert verdict.winner_strategy_id == "A"
    assert verdict.ranking == ["A"]
    assert len(verdict.scorecards) == 1
    assert verdict.scorecards[0].excellence == pytest.approx(1.0)
    assert not verdict.scorecards[0].disqualified


def test_denies_mediocre_but_eligible() -> None:
    """Eligible-but-weak is rejected, not merely deferred."""
    weak = candidate("weak", {"wisdom": 0.2, "courage": 0.2, "temperance": 0.2, "justice": 0.8})
    verdict = InMemoryArbiter().arbitrate(dispute(*[weak]))
    assert verdict.decision is Verdict.DENY
    assert verdict.winner_strategy_id is None


def test_hard_gate_disqualifies_unjust_even_when_best() -> None:
    """A highly scoring candidate that fails Justice cannot win."""
    unjust = candidate(
        "flashy",
        {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.1},
    )
    just = candidate(
        "honest",
        {"wisdom": 0.5, "courage": 0.5, "temperance": 0.5, "justice": 0.9},
    )
    verdict = InMemoryArbiter().arbitrate(dispute(*[unjust, just]))
    # flashy has far higher excellence but fails the hard gate.
    assert verdict.decision is Verdict.ALLOW
    assert verdict.winner_strategy_id == "honest"
    flashy_card = next(s for s in verdict.scorecards if s.candidate_strategy_id == "flashy")
    assert flashy_card.disqualified
    assert "justice" in (flashy_card.disqualify_reason or "")
    assert verdict.ranking[0] == "honest"


def test_all_disqualified_denies_no_winner() -> None:
    """If every candidate violates a hard gate, the dispute is declined."""
    bad1 = candidate("bad1", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.2})
    bad2 = candidate("bad2", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.3})
    verdict = InMemoryArbiter().arbitrate(dispute(*[bad1, bad2]))
    assert verdict.decision is Verdict.DENY
    assert verdict.winner_strategy_id is None
    assert all(s.disqualified for s in verdict.scorecards)


def test_custom_weights_change_winner() -> None:
    """Weighting alter the excellence ranking and thus the winner."""
    weights = VirtueWeights(
        weights={
            CardinalVirtue.WISDOM: 10.0,
            CardinalVirtue.COURAGE: 1.0,
            CardinalVirtue.TEMPERANCE: 1.0,
            CardinalVirtue.JUSTICE: 1.0,
        }
    )
    wise = candidate("wise", {"wisdom": 0.9, "courage": 0.3, "temperance": 0.3, "justice": 0.9})
    strong = candidate("strong", {"wisdom": 0.3, "courage": 0.9, "temperance": 0.9, "justice": 0.9})
    verdict = InMemoryArbiter(weights=weights).arbitrate(dispute(*[strong, wise]))
    assert verdict.winner_strategy_id == "wise"


def test_excellence_tie_defers() -> None:
    """An exact excellence tie is ruled DEFER, never guessed."""
    a = candidate("a", perfect())
    b = candidate("b", perfect())
    verdict = InMemoryArbiter().arbitrate(dispute(*[a, b]))
    assert verdict.decision is Verdict.DEFER
    assert verdict.winner_strategy_id is None


def test_custom_scorer_injection_is_honored() -> None:
    """An injected VirtueScorer supplies the observations."""
    def perfect_scorer(_cand: CandidateOutput, _disp: Dispute) -> dict[CardinalVirtue, float]:
        return {v: 1.0 for v in CardinalVirtue}

    cands = [candidate("x", {}, output="no keywords at all here")]
    verdict = InMemoryArbiter(scorer=perfect_scorer).arbitrate(dispute(*cands))
    # Default keyword fallback would DENY this candidate; the injected scorer
    # rates it perfect, so the win proves injection is honored.
    assert verdict.decision is Verdict.ALLOW
    assert verdict.winner_strategy_id == "x"


def test_default_scorer_keyword_fallback() -> None:
    """Without metadata, the keyword fallback drives scoring deterministically."""
    legal = candidate("legal", {}, output="impartial, fair, lawful, consent, equitable")
    verdict = InMemoryArbiter().arbitrate(dispute(*[legal]))
    justice = verdict.scorecards[0].virtue_scores["justice"]
    assert justice > 0.0
    # Justice is high enough not to trip the hard gate; overall is low -> DENY.
    assert verdict.decision is Verdict.DENY


def test_empty_goal_raises() -> None:
    """A malformed dispute (empty goal) is rejected."""
    with pytest.raises(AreteError):
        InMemoryArbiter().arbitrate(dispute(*[candidate("a", perfect())], goal="   "))


def test_duplicate_strategy_id_raises() -> None:
    """Ambiguous duplicate ids are rejected."""
    with pytest.raises(AreteError):
        InMemoryArbiter().arbitrate(
            dispute(*[candidate("dup", perfect()), candidate("dup", perfect())])
        )


def test_invalid_weights_raise() -> None:
    """A rubric missing a cardinal virtue is invalid."""
    with pytest.raises(AreteError):
        VirtueWeights(
            weights={
                CardinalVirtue.WISDOM: 1.0,
                CardinalVirtue.COURAGE: 1.0,
                CardinalVirtue.TEMPERANCE: 1.0,
            }
        )


def test_deterministic_across_runs() -> None:
    """Identical input yields an identical, reproducible verdict."""
    cands = [
        candidate("a", {"wisdom": 0.8, "courage": 0.6, "temperance": 0.7, "justice": 0.9}),
        candidate("b", {"wisdom": 0.6, "courage": 0.8, "temperance": 0.8, "justice": 0.7}),
    ]
    arbiter = InMemoryArbiter()
    first = arbiter.arbitrate(dispute(*cands))
    second = arbiter.arbitrate(dispute(*cands))
    assert first == second
    assert first.ranking == second.ranking


def test_arbitrator_is_detectable_protocol() -> None:
    """InMemoryArbiter conforms to the Arbitrator protocol at runtime."""
    arbiter: Arbitrator = InMemoryArbiter()
    assert isinstance(arbiter, Arbitrator)


def test_ranking_puts_qualified_first_then_disqualified() -> None:
    """Ranking orders qualified candidates before hard-gate failures."""
    justified = candidate(
        "ok", {"wisdom": 0.7, "courage": 0.7, "temperance": 0.7, "justice": 0.9}
    )
    unjust = candidate(
        "bad", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.1}
    )
    verdict = InMemoryArbiter().arbitrate(dispute(*[unjust, justified]))
    assert verdict.ranking[0] == "ok"
    assert verdict.ranking[1] == "bad"
    assert verdict.winner_strategy_id == "ok"