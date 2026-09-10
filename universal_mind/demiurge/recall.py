"""Memory-aware Demiurge — inject remembered experience into decomposition.

The Demiurge decomposes a goal into sub-intents. This module makes that step
*remembering*: before decomposition, it queries Mnemosyne for the most relevant
prior records (past syntheses, standards, experiments) and attaches them as
``constraints``/``context`` on the resulting sub-intents, so the mind's past
actively shapes its next plan — the "remembering substrate feeds the Demiurge"
promise made concrete.

Deterministic and local; the recall is the same inferential ``query`` used
elsewhere, so there is a single notion of "what the mind remembers".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.intent import Intent
from universal_mind.memory.mnemosyne import Mnemosyne, QueryHit
from universal_mind.memory.store import MemoryStore

from .decompose import DecompositionResult, decompose_intent


@dataclass(frozen=True)
class MemoryAwareDecomposition:
    """A decomposition plus the remembered context it drew upon."""

    decomposition: DecompositionResult
    remembered: tuple[QueryHit, ...]
    context_summary: str


def _format_context(hits: list[QueryHit]) -> str:
    """Flatten the most-relevant memories into a one-line context note."""
    if not hits:
        return ""
    parts = []
    for h in hits[:3]:
        goal = str(h.record.get("payload", {}).get("goal", "") or h.record.get("kind", ""))
        parts.append(f"{h.record.get('kind', 'record')}:{goal}")
    return "remembered: " + " | ".join(parts)


def decompose_with_memory(
    intent: Intent,
    store: MemoryStore,
    *,
    clock: Clock | None = None,
    min_score: float = 0.0,
) -> MemoryAwareDecomposition:
    """Decompose ``intent`` after recalling relevant memories from ``store``.

    The recall is keyed by the intent goal; the top hits (capped) are injected
    onto each sub-intent's constraints so downstream execution can honor past
    experience. The original decomposition logic is unchanged — this only adds
    the remembering layer on top.
    """
    mnemosyne = Mnemosyne(store, clock if clock is not None else SystemClock())
    hits = mnemosyne.query(intent.goal, owner_id=intent.owner_id, min_score=min_score)
    context = _format_context(hits)

    decomposition = decompose_intent(intent)
    if context:
        # Attach the remembered context as an extra constraint on each sub-intent
        # so the plan is explicitly shaped by memory (auditable, not implicit).
        decomposition = DecompositionResult(
            original_intent=decomposition.original_intent,
            sub_intents=[
                sub if context in sub.constraints
                else _with_constraint(sub, context)
                for sub in decomposition.sub_intents
            ],
            execution_order=list(decomposition.execution_order),
        )

    return MemoryAwareDecomposition(
        decomposition=decomposition,
        remembered=tuple(hits),
        context_summary=context,
    )


def _with_constraint(sub: Any, context: str) -> Any:
    """Return a copy of ``sub`` with ``context`` appended to its constraints."""
    from dataclasses import replace

    return replace(sub, constraints=list(sub.constraints) + [context])