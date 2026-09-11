"""Tests for episodic memory — recall when and in what context."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.episodic import (
    Episode,
    recall_episodes,
    record_episode,
)
from universal_mind.memory.store import InMemoryStore


def _clock(iso: str = "2026-09-11T10:00:00") -> FrozenClock:
    return FrozenClock(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc))


def test_record_and_recall_by_context() -> None:
    store = InMemoryStore()
    record_episode(store, owner_id="sovereign", kind="judgment", context="merger", clock=_clock())
    result = recall_episodes(store, "merger")
    assert len(result.episodes) == 1
    assert result.episodes[0].kind == "judgment"
    assert "merger" in result.summary


def test_recall_is_most_recent_first() -> None:
    store = InMemoryStore()
    clock = _clock()
    record_episode(store, owner_id="sovereign", kind="first", context="topic", clock=clock)
    record_episode(store, owner_id="sovereign", kind="second", context="topic", clock=clock.advance(60))
    result = recall_episodes(store, "topic")
    assert result.episodes[0].kind == "second"
    assert result.episodes[1].kind == "first"


def test_recall_filters_by_context() -> None:
    store = InMemoryStore()
    record_episode(store, owner_id="sovereign", kind="a", context="finance", clock=_clock())
    record_episode(store, owner_id="sovereign", kind="b", context="health", clock=_clock())
    result = recall_episodes(store, "finance")
    assert all(e.context == "finance" for e in result.episodes)
    assert len(result.episodes) == 1


def test_recall_respects_owner() -> None:
    store = InMemoryStore()
    record_episode(store, owner_id="alice", kind="a", context="topic", clock=_clock())
    record_episode(store, owner_id="bob", kind="b", context="topic", clock=_clock())
    result = recall_episodes(store, "topic", owner_id="alice")
    assert len(result.episodes) == 1
    assert result.episodes[0].kind == "a"


def test_empty_recall_has_empty_summary() -> None:
    store = InMemoryStore()
    result = recall_episodes(store, "nobody")
    assert result.episodes == ()
    assert result.summary == ""


def test_episode_is_frozen_dataclass() -> None:
    from dataclasses import FrozenInstanceError

    ep = Episode("id", "kind", "ctx", "iso")
    try:
        ep.kind = "changed"  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True