"""Tests for memory-aware Demiurge (recall-then-decompose)."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.core.clock import FrozenClock
from universal_mind.core.intent import Determinism, Intent
from universal_mind.demiurge.recall import decompose_with_memory
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore


def _intent(goal: str) -> Intent:
    return Intent.from_raw(
        raw_text=f"{goal}. Must be done.",
        goal=goal,
        success_criteria=["done"],
        owner_id="owner",
        determinism=Determinism.STRICT,
    )


def _store_with_memory() -> InMemoryStore:
    store = InMemoryStore()
    clock = FrozenClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    m = Mnemosyne(store, clock)
    m.record(
        owner_id="owner",
        kind="synthesis",
        payload={"goal": "summarize security report last week"},
        provenance={"producer": "test"},
    )
    return store


def test_recall_injects_memory_into_sub_intents() -> None:
    store = _store_with_memory()
    result = decompose_with_memory(_intent("summarize the security report"), store, clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert result.remembered, "past synthesis should be recalled"
    assert result.context_summary.startswith("remembered:")
    # The remembered context is attached as a constraint on sub-intents.
    for sub in result.decomposition.sub_intents:
        assert any("remembered:" in c for c in sub.constraints)


def test_no_memory_yields_context_free_decomposition() -> None:
    store = InMemoryStore()
    result = decompose_with_memory(_intent("do an entirely novel thing"), store, clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert not result.remembered
    assert result.context_summary == ""


def test_recall_is_relevant_not_recency_biased() -> None:
    """An unrelated record is not injected under a high relevance floor."""
    store = _store_with_memory()
    result = decompose_with_memory(
        _intent("bake a cake"),
        store,
        clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)),
        min_score=0.5,
    )
    # The only record is about security; baking has no overlap -> no memory.
    assert not result.remembered
    assert result.context_summary == ""


def test_decomposition_still_happens_without_memory() -> None:
    """The underlying decomposition is unchanged when nothing is remembered."""
    store = InMemoryStore()
    result = decompose_with_memory(_intent("write and review"), store, clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert result.decomposition.sub_intents
    assert result.decomposition.execution_order


def test_context_is_auditable() -> None:
    """The remembered context is deterministic and inspectable."""
    store = _store_with_memory()
    r1 = decompose_with_memory(_intent("summarize the security report"), store, clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)))
    r2 = decompose_with_memory(_intent("summarize the security report"), store, clock=FrozenClock(datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert r1.context_summary == r2.context_summary