"""Tests for StandardKeeper rollback — rewind the lineage without erasing history."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}
BETTER = {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}


def _cand(name: str, virtues: dict[str, float] | None = None) -> CandidateOutput:
    return CandidateOutput(strategy_id=name, output=name, metadata={"virtues": virtues or dict(FULL)})


def _keeper() -> StandardKeeper:
    return StandardKeeper(InMemoryStore())


def _seed_two() -> StandardKeeper:
    k = _keeper()
    k.consider(_cand("d1"))
    k.consider(_cand("d2", BETTER))
    return k


def test_rollback_rewinds_depth() -> None:
    k = _seed_two()  # depth 1 (d2)
    res = k.rollback(0, reason="d2 was wrong")
    assert res is not None
    assert res.current_standard.promotion_depth == 0
    assert res.current_standard.name == "d1"


def test_rollback_records_evidence() -> None:
    k = _seed_two()
    res = k.rollback(0, reason="mistake")
    assert res is not None
    assert res.verdict is not None
    assert "mistake" in res.verdict.reasoning
    # The current() now reflects depth 0.
    cur = k.current()
    assert cur is not None and cur.promotion_depth == 0


def test_rollback_out_of_range_returns_none() -> None:
    k = _seed_two()
    assert k.rollback(99) is None
    assert k.rollback(-1) is None


def test_rollback_on_empty_store_returns_none() -> None:
    assert _keeper().rollback(0) is None


def test_history_is_appended_not_erased() -> None:
    k = _seed_two()
    before = len(k.history())
    k.rollback(0)
    after = len(k.history())
    assert after == before + 1  # rollback is a record, not a rewrite


def test_can_grow_forward_again_after_rollback() -> None:
    k = _seed_two()
    k.rollback(0)
    # A new promotion grows from the rewound depth.
    res = k.consider(_cand("d3", BETTER))
    assert res.current_standard.promotion_depth == 1
    assert res.current_standard.name == "d3"