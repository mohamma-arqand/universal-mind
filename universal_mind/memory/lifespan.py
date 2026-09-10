"""Memory lifespan — make the ledger a *living* substrate, not a growing archive.

Mnemosyne records and recalls, but nothing yet keeps the memory *useful* across
runs: an unbounded ledger gets stale, and each run re-queries from scratch. This
module adds the two missing halves:

1. :class:`MemoryBudget` — a soft cap with decay. When the ledger grows past a
   target size, the *least-recently-referenced* records are expired (by TTL) or
   decayed, so the mind keeps its recent, relevant experience and forgets the
   rest — a working memory, not an infinite archive.

2. :class:`MemoryContext` — the remembered context for one run: query Mnemosyne
   for relevant prior records and pack them into a compact, injectable context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.core.clock import Clock, SystemClock
from universal_mind.memory.mnemosyne import Mnemosyne, QueryHit
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class MemoryBudget:
    """A soft cap on live memory plus how aggressively to forget.

    ``max_records`` is the target live size; ``decay_horizon_seconds`` is the
    age past which a record is eligible for decay once we are over budget. This
    is deliberately *soft*: over-budget forgets the oldest first, never errors.
    """

    max_records: int = 500
    decay_horizon_seconds: int = 7 * 24 * 3600  # one week


@dataclass(frozen=True)
class MemoryContextResult:
    """The remembered context assembled for a single run."""

    hits: tuple[QueryHit, ...]
    summary: str
    trimmed: int          # records decayed by the budget pass this run


def recall_context(
    store: MemoryStore,
    text: str,
    *,
    owner_id: str | None = None,
    min_score: float = 0.0,
    limit: int = 8,
    budget: MemoryBudget | None = None,
    clock: Clock | None = None,
) -> MemoryContextResult:
    """Recall relevant memory for ``text`` and apply the budget (decay) pass.

    Deterministic and local: the query is the single inferential recall, and the
    budget pass forgets only records that are both (a) over the soft cap and (b)
    beyond the decay horizon, so fresh/relevant memory is never trimmed. Returns
    the hits, a compact summary, and how many records were trimmed.
    """
    mnemosyne = Mnemosyne(store, clock if clock is not None else SystemClock())
    hits = mnemosyne.query(text, owner_id=owner_id, min_score=min_score, limit=limit)
    summary = _summarize(hits)
    trimmed = _apply_budget(mnemosyne, budget if budget is not None else MemoryBudget())
    return MemoryContextResult(hits=tuple(hits), summary=summary, trimmed=trimmed)


def _summarize(hits: list[QueryHit]) -> str:
    if not hits:
        return ""
    parts = []
    for h in hits[:3]:
        goal = str(h.record.get("payload", {}).get("goal", "") or h.record.get("kind", ""))
        parts.append(f"{h.record.get('kind', 'record')}:{goal}")
    return "remembered: " + " | ".join(parts)


def _apply_budget(mnemosyne: Mnemosyne, budget: MemoryBudget) -> int:
    """Forget the *least-significant* records once the live ledger exceeds cap.

    Unlike a naive oldest-first expiry, this ranks eligible (beyond-horizon)
    records by a value weight derived from kind/provenance — so a human-consented
    standard survives while a one-off failed note is trimmed first. Forgetting is
    thus evidence-shaped (judgment, not recency) while still never touching
    fresh/relevant memory. Returns the number trimmed; a store without a
    delete/compaction path keeps the records (soft, never errors).
    """
    from datetime import datetime, timedelta, timezone

    records = list(mnemosyne.store.read_all())
    live = len(records)
    if live <= budget.max_records:
        return 0

    excess = live - budget.max_records
    trimmed = 0
    horizon = timedelta(seconds=budget.decay_horizon_seconds)
    now = mnemosyne.clock.now()

    # Eligible = beyond the horizon; then rank by significance (lowest first).
    eligible: list[dict[str, Any]] = []
    for record in records:
        created_raw = record.get("created_at")
        if not isinstance(created_raw, str):
            continue
        try:
            created = datetime.fromisoformat(created_raw)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if (now - created) > horizon:
            eligible.append(record)

    # Lowest significance first (then older as a tie-break), so we forget the
    # least-valuable, not merely the oldest.
    eligible.sort(key=lambda r: (_significance(r), r.get("created_at", "")))
    for record in eligible:
        if trimmed >= excess:
            break
        rid = record.get("id")
        if rid and _safe_delete(mnemosyne, rid):
            trimmed += 1
    return trimmed


def _significance(record: dict[str, Any]) -> int:
    """A value weight for a record, derived from kind and evidence markers.

    Higher is more worth keeping: human consent / a standing standard are the
    most significant; a failed or unremarkable record the least. Deterministic
    and purely descriptive — it only *ranks* forgetting order, nothing else.
    """
    kind = str(record.get("kind", ""))
    payload = record.get("payload")
    if kind in ("human_consent", "standard"):
        return 90
    if kind == "synthesis":
        if isinstance(payload, dict) and payload.get("verified") is True:
            return 70
        return 40
    if kind == "generated_power":
        return 60
    if kind == "feedback":
        return 50
    return 10


def _safe_delete(mnemosyne: Mnemosyne, record_id: str) -> bool:
    """Delete a record if the store supports it; otherwise a soft no-op."""
    try:
        return mnemosyne.store.delete(record_id)
    except NotImplementedError:
        return False