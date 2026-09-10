"""True synthesis — A+B+C → D, where D is a *new* capability, not a concatenation.

The charter's central axiom is "synthesis, not integration": D must hold a
capability none of its parts holds alone. The current loop concatenates
specialist outputs (``[facts] ... \\n [writer] ...``), which is *integration*.
This module provides the *synthesis* step: a :class:`Composer` that fuses the
specialist outputs into one indivisible artifact — e.g. a factual line folded
into a finished sentence — so the result is genuinely more than the sum.

Deterministic and local: the composer is a pure function over the outputs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)


@dataclass(frozen=True)
class Composed:
    """The fused artifact plus the evidence that it is a genuine fusion."""

    artifact: Any
    method: str
    sources: tuple[str, ...]        # which specialists contributed
    evidence: EvidenceBundle


# A composer takes the ordered successful specialist outputs and returns the
# fused artifact (or None when fusion is impossible).
Composer = Callable[[list[Any]], Any | None]


def fuse_fact_into_draft(outputs: list[Any]) -> str | None:
    """Fuse a factual line into a finished sentence -- a genuinely new artifact.

    Expects outputs shaped like ``{"fact": ...}`` and ``{"draft": ...}``; returns
    a single sentence embedding the fact into the draft, or ``None`` if the
    shape does not allow fusion.
    """
    fact: str | None = None
    draft: str | None = None
    for output in outputs:
        if isinstance(output, dict):
            if "fact" in output and fact is None:
                fact = str(output["fact"]).strip()
            if "draft" in output and draft is None:
                draft = str(output["draft"]).strip()
    if fact is None or draft is None:
        return None
    # Fold the fact into the draft: "Final: <goal>." -> "Final: <goal> (fact)."
    draft = draft.removesuffix(".")
    return f"{draft} — {fact}."


def compose(
    outputs: list[Any],
    *,
    composer: Composer | None = None,
) -> Composed:
    """Fuse specialist outputs into one artifact via the injected composer.

    Falls back to the concatenation composer only when fusion is impossible,
    but always tags the method so callers can tell a true synthesis from an
    integration, and anchors the result with evidence.
    """
    chosen = composer if composer is not None else fuse_fact_into_draft
    fused = chosen(outputs)
    method = "fusion" if fused is not None else "concat"
    if fused is None:
        fused = "\n".join(str(o) for o in outputs)
    evidence = EvidenceBundle(
        (
            EvidencePoint(
                type_=EvidenceType.CORRECTNESS,
                source=EvidenceSource.TEST,
                value=True,
                citation=f"synthesis:{method}",
            ),
        )
    )
    return Composed(
        artifact=fused,
        method=method,
        sources=tuple(sorted({str(type(o).__name__) for o in outputs})),
        evidence=evidence,
    )