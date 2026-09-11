"""Goal-drift detection — notice when the path has left the original goal.

A mind that keeps executing without checking whether it is still doing what it
set out to do is the classic failure of the over-eager agent. This module is the
drift detector: it measures the *distance* between the stated goal and what was
actually produced, and flags drift when the outcome no longer reflects the goal's
intent — so the mind can pause and re-align instead of confidently finishing the
wrong thing.

Deterministic and local: a closed-form lexical-overlap distance (no I/O), with a
configurable threshold.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftAssessment:
    """Whether the produced outcome has drifted from the stated goal."""

    drift: bool
    overlap: float            # 0..1 lexical overlap between goal and outcome
    threshold: float
    reason: str


def _tokens(text: str) -> set[str]:
    """A small, deterministic tokenization: lowercase alphanumeric word stems."""
    import re

    lowered = text.lower()
    return {t for t in re.findall(r"[a-z0-9]{3,}", lowered)}


def assess_goal_drift(goal: str, outcome: str, *, threshold: float = 0.3) -> DriftAssessment:
    """Measure lexical-overlap between goal and outcome; flag drift when below threshold.

    ``overlap`` is the Jaccard similarity of the two token sets — if the outcome
    shares almost no substantives with the goal, the mind has likely drifted.
    A high overlap (>= threshold) means the outcome still reflects the goal.
    """
    goal_tokens = _tokens(goal)
    outcome_tokens = _tokens(outcome)

    if not goal_tokens:
        return DriftAssessment(drift=False, overlap=0.0, threshold=threshold, reason="no goal tokens to compare")

    if not outcome_tokens:
        return DriftAssessment(
            drift=True, overlap=0.0, threshold=threshold,
            reason="outcome has no substantive tokens — produced nothing toward the goal",
        )

    intersection = goal_tokens & outcome_tokens
    union = goal_tokens | outcome_tokens
    overlap = len(intersection) / len(union) if union else 0.0

    if overlap < threshold:
        return DriftAssessment(
            drift=True, overlap=round(overlap, 4), threshold=threshold,
            reason=f"outcome shares only {overlap:.0%} of the goal's substance — likely drifted",
        )
    return DriftAssessment(
        drift=False, overlap=round(overlap, 4), threshold=threshold,
        reason=f"outcome retains {overlap:.0%} of the goal's substance — on course",
    )