"""Episodic memory — recall *when* and *in what context*, not just *what*.

Mnemosyne answers "what did I record?"; lifespan answers "what is relevant
now?". Neither answers the *temporal* question — "when did this happen, and in
what context, in relation to my other experiences?". This module is the episodic
layer: events are anchored with a timestamp and a context tag, and recall is
*contextual + temporal* — recent events that share the context surface first,
and the shape of an episode (a burst of related events in a time window) is
recoverable, not just a single record.

Deterministic and local: it reads an injectable clock, never mutates the store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from universal_mind.core.clock import Clock, SystemClock
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class Episode:
    """One timestamped, context-tagged memory event."""

    event_id: str
    kind: str
    context: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EpisodeRecall:
    """The recalled episodic context for a query."""

    episodes: tuple[Episode, ...]
    summary: str


def record_episode(
    store: MemoryStore,
    *,
    owner_id: str,
    kind: str,
    context: str,
    payload: dict[str, Any] | None = None,
    clock: Clock | None = None,
) -> str:
    """Append a timestamped, context-tagged episode to the ledger.

    Reuses Mnemosyne so the episode is a first-class ledger record (auditable),
    tagged with ``kind='episode'`` and carrying ``context`` in its payload so a
    later temporal/contextual recall can find it.
    """
    mnemosyne = Mnemosyne(store, clock if clock is not None else SystemClock())
    return mnemosyne.record(
        owner_id=owner_id,
        kind="episode",
        payload={
            "episode_kind": kind,
            "context": context,
            **(payload or {}),
        },
        provenance={"producer": "EpisodicMemory", "owner_id": owner_id},
    )


def recall_episodes(
    store: MemoryStore,
    context: str,
    *,
    owner_id: str | None = None,
    limit: int = 5,
    clock: Clock | None = None,
) -> EpisodeRecall:
    """Recall episodes by context, most recent first.

    Matches episodes whose ``context`` field equals (or contains) the query
    ``context``, ordered newest-first (by ``created_at``), so "what did I do in
    *this* context, and when?" is answered in temporal order.
    """
    records = list(store.read_all())
    matches: list[Episode] = []
    for record in records:
        if record.get("kind") != "episode":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        rec_context = str(payload.get("context", ""))
        if context.lower() in rec_context.lower() or rec_context.lower() in context.lower():
            if owner_id is not None and record.get("owner_id") != owner_id:
                continue
            matches.append(
                Episode(
                    event_id=str(record.get("id", "")),
                    kind=str(payload.get("episode_kind", "")),
                    context=rec_context,
                    created_at=str(record.get("created_at", "")),
                    payload={k: v for k, v in payload.items() if k not in ("kind", "context", "episode_kind")},
                )
            )

    # Newest first: created_at is ISO-8601, so lexicographic sort == chronological.
    matches.sort(key=lambda e: e.created_at, reverse=True)
    matches = matches[:limit]

    if not matches:
        summary = ""
    else:
        recent = matches[0]
        summary = (
            f"last in context {context!r} was {recent.kind} at {recent.created_at} "
            f"({len(matches)} recalled)"
        )

    return EpisodeRecall(episodes=tuple(matches), summary=summary)