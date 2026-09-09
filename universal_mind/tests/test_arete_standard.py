"""Tests for the ARETĒ critical loop — promote a D only when ARETĒ rules it better."""

from __future__ import annotations

from pathlib import Path

from universal_mind.arete import (
    PromotionDecision,
    StandardKeeper,
)
from universal_mind.arete.standard import Standard, _as_candidate
from universal_mind.memory.store import InMemoryStore, LocalJSONLStore, MemoryStore
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, virtues: dict[str, float], output: object = "artifact") -> CandidateOutput:
    return CandidateOutput(strategy_id=strategy_id, output=output, metadata={"virtues": virtues})


def _keeper(store: MemoryStore) -> StandardKeeper:
    return StandardKeeper(store)


DEFAULT = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}


def test_first_election_seeds_standard() -> None:
    """No incumbent -> the first proposal becomes the standard (uncontested)."""
    store = InMemoryStore()
    keeper = _keeper(store)
    res = keeper.consider(_candidate("D1", DEFAULT))
    assert res.decision is PromotionDecision.PROMOTED
    assert res.previous_standard is None
    assert res.current_standard.name == "D1"
    cur = keeper.current()
    assert cur is not None and cur.name == "D1"


def test_better_d_promotes() -> None:
    """A strictly stronger contender overturns the standing standard."""
    store = InMemoryStore()
    keeper = _keeper(store)
    keeper.consider(_candidate("D1", DEFAULT))
    # D2 is stronger than the incumbent (wisdom 0.9 baseline on incumbents).
    res = keeper.consider(_candidate("D2", {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}))
    assert res.decision is PromotionDecision.PROMOTED
    assert res.current_standard.name == "D2"
    assert res.current_standard.promotion_depth == 1
    cur = keeper.current()
    assert cur is not None and cur.name == "D2"


def test_weaker_d_rejected() -> None:
    """A contender that does not clear the incumbent's evidence bar is rejected."""
    store = InMemoryStore()
    keeper = _keeper(store)
    keeper.consider(_candidate("D1", DEFAULT))
    res = keeper.consider(_candidate("D2", {"justice": 1.0, "wisdom": 0.5, "courage": 1.0, "temperance": 1.0}))
    assert res.decision is PromotionDecision.REJECTED
    assert res.current_standard.name == "D1"  # incumbent survives


def test_justice_gate_rejects_even_high_excellence() -> None:
    """Non-compensatory rule: a justice-violating contender is denied regardless."""
    store = InMemoryStore()
    keeper = _keeper(store)
    keeper.consider(_candidate("D1", DEFAULT))
    res = keeper.consider(
        _candidate("D2", {"justice": 0.1, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0})
    )
    assert res.decision is PromotionDecision.REJECTED  # disqualified by hard gate
    assert res.current_standard.name == "D1"


def test_promotion_append_only_ledger() -> None:
    """Every promotion is persisted; history is a replayable audit trail."""
    store = InMemoryStore()
    keeper = _keeper(store)
    keeper.consider(_candidate("D1", DEFAULT))
    keeper.consider(_candidate("D2", DEFAULT))
    hist = keeper.history()
    assert len(hist) == 2
    assert hist[0]["payload"]["name"] == "D1"
    assert hist[1]["payload"]["name"] == "D2"
    assert hist[1]["payload"]["promotion_depth"] == 1


def test_recency_alone_never_promotes() -> None:
    """A merely-equal newcomer ties and is deferred, not promoted."""
    store = InMemoryStore()
    keeper = _keeper(store)
    keeper.consider(_candidate("D1", DEFAULT))
    # D2 equals the incumbent on every virtue (wisdom 0.9, the incumbent's bar);
    # only a strict improvement wins.
    res = keeper.consider(_candidate("D2", {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}))
    assert res.decision is PromotionDecision.DEFERRED
    assert res.current_standard.name == "D1"


def test_standard_roundtrips_through_ledger(tmp_path: Path) -> None:
    """The Standard object survives a reload from a fresh keeper on the same store."""
    store = LocalJSONLStore(directory=tmp_path)
    k1 = _keeper(store)
    k1.consider(_candidate("D1", DEFAULT, "the-artifact"))
    k2 = _keeper(store)
    current = k2.current()
    assert current is not None
    assert current.name == "D1"
    assert current.artifact == "the-artifact"


def test_as_candidate_metadata() -> None:
    """The incumbent is scored strong-but-improvable, never at 1.0 wisdom."""
    std = Standard(name="s", artifact="a", promotion_depth=2)
    cand = _as_candidate(std)
    assert cand.strategy_id == "standard:s"
    assert cand.metadata["virtues"]["wisdom"] < 1.0
    assert cand.metadata["promotion_depth"] == 2