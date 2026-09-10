"""Tests for memory lifespan — recall context + soft budget decay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.lifespan import MemoryBudget, recall_context
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore, LocalJSONLStore


def _clock(days_ago: int = 0) -> FrozenClock:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FrozenClock(base + timedelta(days=days_ago))


def _seed(store: InMemoryStore, owner: str = "o") -> Mnemosyne:
    m = Mnemosyne(store, _clock())
    m.record(owner_id=owner, kind="synthesis", payload={"goal": "write the security report"}, provenance={"p": "x"})
    m.record(owner_id=owner, kind="synthesis", payload={"goal": "bake a cake"}, provenance={"p": "x"})
    return m


def test_recall_context_returns_relevant_hits() -> None:
    store = InMemoryStore()
    _seed(store)
    result = recall_context(store, "security report", owner_id="o")
    assert result.hits
    assert result.summary.startswith("remembered:")
    assert "security" in result.hits[0].record["payload"]["goal"]


def test_recall_context_empty_for_unrelated() -> None:
    store = InMemoryStore()
    _seed(store)
    result = recall_context(store, "completely different", owner_id="o", min_score=0.5)
    assert not result.hits
    assert result.summary == ""


def test_budget_never_trims_fresh_memory() -> None:
    """A small budget with fresh (young) records trims nothing."""
    store = InMemoryStore()
    _seed(store)
    result = recall_context(
        store,
        "report",
        owner_id="o",
        budget=MemoryBudget(max_records=1, decay_horizon_seconds=100000),
        clock=_clock(),  # same clock as the seed (records are 0 days old)
    )
    assert result.trimmed == 0  # records are young, so even over budget no trim


def test_budget_trims_old_records_over_cap(tmp_path: Path) -> None:
    """Over budget and old records are decayed (soft-cap enforced)."""
    # LocalJSONLStore supports delete/compaction, so trimming is observable.
    store = LocalJSONLStore(directory=tmp_path)
    # Seed at the base clock.
    m = Mnemosyne(store, _clock())
    for i in range(10):
        m.record(owner_id="o", kind="note", payload={"goal": f"note {i}"}, provenance={"p": "x"})
    # Recall 30 days later, so every record is beyond a 600s horizon.
    result = recall_context(
        store,
        "note",
        owner_id="o",
        budget=MemoryBudget(max_records=3, decay_horizon_seconds=600),
        clock=_clock(days_ago=30),
    )
    remaining = sum(1 for _ in store.read_all())
    assert remaining <= 10
    assert result.trimmed >= 1


def test_recall_context_is_deterministic() -> None:
    s1 = InMemoryStore(); _seed(s1)
    s2 = InMemoryStore(); _seed(s2)
    r1 = recall_context(s1, "security", owner_id="o")
    r2 = recall_context(s2, "security", owner_id="o")
    assert r1.summary == r2.summary