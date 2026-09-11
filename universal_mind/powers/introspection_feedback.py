"""Evolutionary architecture — route introspection insights back into generation.

The mind already *produces* knowledge every cycle — rejected branches,
best-losing contenders, the acceptance bar, the execution budget, the health
self-assessment — but that knowledge was a dead end: reported, then forgotten.
This module closes the growth loop by turning those insights into *constraints*
that shape the next generation.

The mechanism is a :class:`PowerGenerator` (the same injectable generator Power
Zero already uses) that bake the insight into the description it emits — so the
next generated power is literally derived from what the last cycle learned.
Fully deterministic: given the same insights, the same shaped generator results.

Pure and local: it reads the loop's reactive state, never mutates it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GenerationInsight:
    """One bearing the mind extracted from a finished cycle and will re-apply."""

    rejected_branches: tuple[str, ...]
    best_loser: str | None
    acceptance_bar: float
    budget: float
    unhealthy: bool


def extract_insights(loop: Any) -> GenerationInsight:
    """Distill a self-awareness loop's reactive state into generation constraints."""
    lineage = getattr(loop, "lineage", None)
    rejected: tuple[str, ...] = ()
    best_loser: str | None = None
    if lineage is not None:
        rb = getattr(lineage, "rejected_branches", None)
        if callable(rb):
            rejected = tuple(rb())
        blc = getattr(lineage, "best_losing_contender", None)
        if callable(blc):
            best = blc()
            best_loser = best.contender if best is not None else None

    bar = getattr(loop, "acceptance_bar", 0.9)
    budget = getattr(loop, "budget", 100.0)
    # Unhealthy is read from the reactive bar (a raised bar means self-correction
    # already fired), consistent with ConscientiousMouth — not a fresh health
    # query, which would say "healthy" for an empty lineage.
    unhealthy = bool(bar is not None and bar >= 0.95)

    return GenerationInsight(
        rejected_branches=rejected,
        best_loser=best_loser,
        acceptance_bar=float(bar),
        budget=float(budget),
        unhealthy=unhealthy,
    )


def shaped_description(name: str, base_desc: str, insight: GenerationInsight) -> str:
    """Bake the insight into a richer description that will constrain generation.

    The insight becomes *wording* the default Power Zero generator keys off of, so
    a raised bar (more careful) or a cut budget (cheaper) actually changes what
    the next power does, not just its label.
    """
    parts = [base_desc.strip()]
    if insight.unhealthy:
        parts.append("be economical and conservative")
    else:
        parts.append("be thorough")
    if insight.rejected_branches:
        parts.append("avoid repeating " + ", ".join(insight.rejected_branches[:3]))
    if insight.best_loser:
        parts.append(f"improve on the near-miss '{insight.best_loser}'")
    parts.append(f"respect budget {insight.budget:.1f} and bar {insight.acceptance_bar:.2f}")
    return " ; ".join(parts)


def make_insight_driven_generator(
    loop: Any,
    *,
    base_generator: Any | None = None,
) -> Any:
    """Return a :class:`PowerGenerator` that shapes each description by the loop's insight.

    The returned callable has the ``(name, description) -> (source, expected)``
    contract Power Zero expects, but first rewrites ``description`` through
    :func:`shaped_description` so the generated power is constrained by the last
    cycle's learning. When ``base_generator`` is None, the default Power Zero
    generator is used.
    """
    from universal_mind.powers.generator import _default_generator

    base = base_generator if base_generator is not None else _default_generator

    def shaped(name: str, description: str) -> tuple[str, Any]:
        insight = extract_insights(loop)
        new_desc = shaped_description(name, description, insight)
        return base(name, new_desc)

    return shaped