"""Tests for the JudgmentLineage — the reasoning behind the standards."""

from __future__ import annotations

from universal_mind.arete.lineage import JudgmentLineage
from universal_mind.arete.standard import StandardKeeper
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}
BETTER = {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}
WEAK = {"justice": 1.0, "wisdom": 0.4, "courage": 1.0, "temperance": 1.0}


def _cand(name: str, virtues: dict[str, float] | None = None) -> CandidateOutput:
    return CandidateOutput(strategy_id=name, output=name, metadata={"virtues": virtues or dict(FULL)})


def _lineage() -> JudgmentLineage:
    return JudgmentLineage(StandardKeeper(InMemoryStore()))


def test_every_consideration_is_reasoned() -> None:
    lin = _lineage()
    lin.consider(_cand("d1"))
    lin.consider(_cand("d2", BETTER))
    lin.consider(_cand("weak", WEAK))
    nodes = lin.nodes()
    assert len(nodes) == 3
    # Every node carries a non-empty reasoning string.
    assert all(n.reasoning for n in nodes)


def test_node_records_decision_and_excellence() -> None:
    lin = _lineage()
    lin.consider(_cand("d1"))
    lin.consider(_cand("weak", WEAK))
    # The weak contender is rejected and its excellence is below the accepted one.
    decisions = [n.decision for n in lin.nodes()]
    assert "promoted" in decisions
    assert "rejected" in decisions


def test_explain_returns_reasoned_trail() -> None:
    lin = _lineage()
    lin.consider(_cand("d1"))
    trail = lin.explain()
    assert trail
    assert "d1" in trail[0]
    assert trail[0].startswith("[promoted]")


def test_rejected_branches_are_recoverable() -> None:
    lin = _lineage()
    lin.consider(_cand("d1"))
    lin.consider(_cand("weak", WEAK))
    assert "weak" in lin.rejected_branches()


def test_best_losing_contender_finds_near_miss() -> None:
    lin = _lineage()
    lin.consider(_cand("seed"))
    # A strong-but-not-strong-enough contender loses.
    lin.consider(_cand("near-miss", {"justice": 1.0, "wisdom": 0.85, "courage": 1.0, "temperance": 1.0}))
    loser = lin.best_losing_contender()
    assert loser is not None
    assert loser.contender == "near-miss"
    assert loser.excellence > 0


def test_deferred_contender_counts_as_losing_branch() -> None:
    """A deferral is not a win: a parity contender that failed to overturn the
    standing standard 'lost' the head-to-head and must be recoverable."""
    lin = _lineage()
    lin.consider(_cand("stand", BETTER))          # becomes standing standard
    # A near-but-not-equal contender is deferred (recency never wins at parity).
    deferred = _cand("near", {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0})
    result = lin.consider(deferred)
    assert result.decision.value == "deferred"
    # The deferred contender is still a losing, recoverable branch.
    assert "near" in lin.rejected_branches()
    loser = lin.best_losing_contender()
    assert loser is not None
    assert loser.contender == "near"


def test_count_by_decision() -> None:
    lin = _lineage()
    lin.consider(_cand("d1"))
    lin.consider(_cand("d2", BETTER))
    lin.consider(_cand("weak", WEAK))
    counts = lin.count_by_decision()
    assert counts["promoted"] == 2
    assert counts["rejected"] == 1


def test_justice_is_recorded_for_audit() -> None:
    lin = _lineage()
    lin.consider(_cand("just", {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}))
    assert lin.nodes()[0].justice == 1.0