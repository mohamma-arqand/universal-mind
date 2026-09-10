"""Sovereign context — a compressed "who I am" injected into every interaction.

MOUTH is the *one identity and one point of interaction*, but each run is
currently stateless: the mind has no continuous self between turns. This module
distills the ledger's history (standards, syntheses, experiments, human rulings)
into a compact, stable `SovereignContext` that rides into every new intent, so
the user talks to a *mind with a memory and a self*, not a stateless function.

Deterministic and local: the summary is derived solely from the ledger, keyed by
the most recent standards and the kinds of experience accumulated.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.core.clock import Clock
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class SovereignContext:
    """A compact, stable self-description distilled from the ledger."""

    identity_line: str            # "ONE MIND · MANY MINDS · ONE INTEGRATED JUDGMENT"
    current_standard: str | None  # the last promoted standard's name
    lineage_depth: int            # how deep the standard lineage has grown
    experience: tuple[str, ...]   # kinds of experience accumulated (deduped)
    summary: str                  # a single human/self-readable digest


def build_sovereign_context(
    store: MemoryStore,
    *,
    clock: Clock | None = None,
    owner: Identity = DEFAULT_OWNER,
) -> SovereignContext:
    """Distill the ledger into a compact self-context.

    The current standard and its lineage depth come from the most recent
    ``standard`` record; ``experience`` is the sorted, deduped set of record
    kinds so far, so the mind knows what it has done. The ``summary`` is a
    stable one-line digest that can be prepended to any intent as a personal
    preamble.
    """
    records = list(store.read_all())

    standards = [r for r in records if r.get("kind") == "standard"]
    current_standard: str | None = None
    lineage_depth = 0
    if standards:
        latest = standards[-1]
        payload = latest.get("payload", {})
        current_standard = str(payload.get("name") or None)
        lineage_depth = int(payload.get("promotion_depth", 0) or 0)

    experience = tuple(sorted({str(r.get("kind")) for r in records if r.get("kind")}))
    identity_line = "ONE MIND · MANY MINDS · ONE INTEGRATED JUDGMENT"

    if current_standard:
        summary = (
            f"{identity_line} — standing standard <{current_standard}> at depth "
            f"{lineage_depth}; experienced {', '.join(experience) or 'nothing yet'}."
        )
    else:
        summary = f"{identity_line} — no standing standard yet; experienced {', '.join(experience) or 'nothing'}."

    return SovereignContext(
        identity_line=identity_line,
        current_standard=current_standard,
        lineage_depth=lineage_depth,
        experience=experience,
        summary=summary,
    )


def inject_preamble(raw_text: str, context: SovereignContext) -> str:
    """Prepend the self-context as a personal preamble to an incoming utterance.

    Deterministic: the result is ``summary + " " + raw_text``, so MOUTH still
    parses the goal unchanged while the mind's identity rides alongside it as
    context (an explicit, auditable carrier, never silently mutated).
    """
    return f"{context.summary} {raw_text}".strip()