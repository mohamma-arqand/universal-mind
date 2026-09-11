"""Epistemic uncertainty — know what you do not know, and say so.

A judge that must always pick a winner will pick a wrong one when the evidence
is thin. This module is the epistemic layer: given a decision and the evidence
behind it, it decides whether the mind *actually knows enough* to commit — and
when it does not, it returns an honest ``UNKNOWN`` with a reason instead of a
guess. "I don't know" becomes a first-class epistemic outcome, not a failure.

The signal is evidence-based: a decision whose supporting evidence is absent,
zero-weight, or too weak relative to the cost of being wrong is judged UNKNOWN.
Deterministic and pure — it reads a verdict + evidence, mutates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EpistemicStatus(str, Enum):
    """Whether the mind knows enough to commit."""

    KNOWN = "known"          # evidence sufficient; proceed with the decision
    UNKNOWN = "unknown"      # evidence insufficient; report "I don't know"
    CONFLICTED = "conflicted"  # evidence contradicts; do not commit


@dataclass(frozen=True)
class UncertaintyAssessment:
    """The epistemic verdict on a decision, with its reason."""

    status: EpistemicStatus
    reason: str
    evidence_weight: float          # total weight of the supporting evidence


def assess_uncertainty(
    evidence_weight: float,
    *,
    min_weight: float = 0.5,
    conflicts: int = 0,
) -> UncertaintyAssessment:
    """Assess whether a decision is epistemically safe to commit to.

    - ``evidence_weight`` is the total measured support for the decision;
      below ``min_weight`` the mind does not know enough -> UNKNOWN.
    - ``conflicts`` counts explicit pieces of evidence that contradict the
      decision; any positive count means the decision is CONFLICTED, regardless
      of how much supporting weight it has (one genuine counter-evidence
      upends commitment).

    Returns a reasoned status + the reason, never a bare guess.
    """
    if conflicts > 0:
        return UncertaintyAssessment(
            status=EpistemicStatus.CONFLICTED,
            reason=f"counter-evidence present ({conflicts} conflicting point(s)); do not commit",
            evidence_weight=evidence_weight,
        )
    if evidence_weight < min_weight:
        return UncertaintyAssessment(
            status=EpistemicStatus.UNKNOWN,
            reason=f"supporting evidence weight {evidence_weight:.2f} is below {min_weight:.2f}; not enough to know",
            evidence_weight=evidence_weight,
        )
    return UncertaintyAssessment(
        status=EpistemicStatus.KNOWN,
        reason=f"supporting evidence weight {evidence_weight:.2f} is sufficient",
        evidence_weight=evidence_weight,
    )


def assess_verdict_uncertainty(verdict: Any, *, min_weight: float = 0.5, conflicts: int = 0) -> UncertaintyAssessment:
    """Assess the epistemic safety of an arbitration verdict.

    Reads the verdict's own ``evidence.total_weight()`` as the support measure, so
    a verdict that cannot show enough evidence is flagged UNKNOWN — tying the
    epistemic layer directly to the auditable evidence discipline.
    """
    evidence = getattr(verdict, "evidence", None)
    weight = 0.0
    if evidence is not None and hasattr(evidence, "total_weight"):
        weight = evidence.total_weight()
    return assess_uncertainty(weight, min_weight=min_weight, conflicts=conflicts)