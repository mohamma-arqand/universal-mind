"""Rubric learning — the evaluation rubric improves from its own mistakes.

A fixed rubric is a frozen prejudice: if it keeps deferring (never decisive) or
keeps accepting weak work, it never adapts. This module lets the rubric *learn*
from its own track record. Given a short history of arbitration outcomes, it
produces a new :class:`VirtueWeights` that corrects the observed failure mode —
raise the accept threshold when weak work was accepted, lower the tie-epsilon is
not needed but raise the accept bar when deferrals pile up — an immutable
evolution, not a mutation.

Deterministic and pure: it reads outcomes, returns a fresh rubric; the old one
is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.arete.virtue import VirtueWeights


@dataclass(frozen=True)
class RubricLearning:
    """The newly-learned rubric and what changed."""

    weights: VirtueWeights
    accept_threshold: float
    reason: str


def learn_rubric(
    outcomes: list[str],
    *,
    base: VirtueWeights | None = None,
) -> RubricLearning:
    """Evolve a rubric from a short history of ``outcomes`` (verdict slugs).

    Failure modes detected:
    - a history of ``defer`` (never decisive) -> raise the accept threshold and
      tighten the tie-epsilon, so the rubric stops failing to commit;
    - a history of ``deny`` (too strict) -> lower the accept threshold slightly,
      so reasonable work is not refused;
    - a history of ``allow`` -> leave the rubric as-is (it is working).

    Returns a fresh, immutable rubric derived from the base (never mutated).
    """
    base = base if base is not None else VirtueWeights()
    threshold = base.accept_threshold

    defers = outcomes.count("defer")
    denies = outcomes.count("deny")
    total = len(outcomes)

    if total == 0:
        return RubricLearning(weights=base, accept_threshold=threshold, reason="no history to learn from")

    if defers >= total * 0.5:
        # Chronic indecision: raise the bar the arbiter must clear to commit,
        # making a stronger stance explicit rather than deferring.
        threshold = min(1.0, threshold + 0.1)
        reason = f"{defers}/{total} deferrals — raised accept threshold to {threshold:.2f}"
    elif denies >= total * 0.5:
        # Chronic refusal: the rubric is too strict; ease the bar.
        threshold = max(0.1, threshold - 0.05)
        reason = f"{denies}/{total} denials — lowered accept threshold to {threshold:.2f}"
    else:
        reason = "mostly allowed — rubric is working, kept as-is"

    learned = VirtueWeights(
        weights=dict(base.weights),
        hard_gate=frozenset(base.hard_gate),
        hard_gate_threshold=base.hard_gate_threshold,
        accept_threshold=threshold,
        tie_epsilon=base.tie_epsilon,
    )
    return RubricLearning(weights=learned, accept_threshold=threshold, reason=reason)