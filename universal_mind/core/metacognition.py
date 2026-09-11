"""Metacognition — the mind reasoning about its own reasoning.

The deepest cognitive move is not a new kind of reasoning, but *reasoning about
reasoning*. This module is the metacognitive layer: it takes the mind's own
reasoning products — a counterfactual robustness check, an epistemic-uncertainty
assessment, a hypothesis-ensemble convergence — and folds them into ONE reasoned
"how much should I trust this decision?" judgment. It does not re-judge the
world; it judges the *quality of the judging itself*.

Deterministic and pure: it reads those three prior products, emits a confidence
band and a plain explanation, never mutates anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from universal_mind.arete.counterfactual import CounterfactualResult
from universal_mind.arete.uncertainty import EpistemicStatus
from universal_mind.demiurge.hypotheses import EnsembleResult


class MetaConfidence(str, Enum):
    """The metacognitive confidence band for a decision."""

    HIGH = "high"        # robust, known, and converged
    MEDIUM = "medium"    # sound on most axes, weak on one
    LOW = "low"          # fragile / unknown / unconverged
    SKEPTICAL = "skeptical"  # multiple axes fail — do not trust


@dataclass(frozen=True)
class MetacognitiveVerdict:
    """The mind's reasoned judgment about how much to trust a decision."""

    confidence: MetaConfidence
    axes: dict[str, bool]          # axis name -> passed
    explanation: str


def _axis_strength(
    counterfactual: CounterfactualResult | None,
    uncertainty_status: EpistemicStatus | None,
    ensemble: EnsembleResult | None,
) -> dict[str, bool]:
    """Map each self-reasoning product to a pass/fail axis."""
    axes: dict[str, bool] = {}
    axes["robust"] = counterfactual.robust if counterfactual is not None else False
    axes["known"] = (
        uncertainty_status is EpistemicStatus.KNOWN if uncertainty_status is not None else False
    )
    axes["converged"] = ensemble.converged if ensemble is not None else False
    return axes


def assess_metacognition(
    counterfactual: CounterfactualResult | None = None,
    uncertainty_status: EpistemicStatus | None = None,
    ensemble: EnsembleResult | None = None,
) -> MetacognitiveVerdict:
    """Fold three self-reasoning products into a metacognitive confidence band.

    The band is the *count of passing axes*, not a weighted score — a
    decision is only trusted when several independent self-checks agree:
    - all three pass -> HIGH,
    - exactly two pass -> MEDIUM,
    - exactly one passes and it is "robust" -> LOW,
    - otherwise -> SKEPTICAL (do not trust).

    The confidence never overrides the decision; it *annotates* it with a
    reasoned "how should I feel about what I just decided?".
    """
    axes = _axis_strength(counterfactual, uncertainty_status, ensemble)
    passed = sum(1 for ok in axes.values() if ok)

    if passed == 3:
        confidence = MetaConfidence.HIGH
    elif passed == 2:
        confidence = MetaConfidence.MEDIUM
    elif passed == 1 and axes.get("robust", False):
        confidence = MetaConfidence.LOW
    else:
        confidence = MetaConfidence.SKEPTICAL

    failing = [name for name, ok in axes.items() if not ok]
    if failing:
        explanation = f"self-checks not passed: {', '.join(failing)}"
    else:
        explanation = "all self-checks passed"

    return MetacognitiveVerdict(confidence=confidence, axes=axes, explanation=explanation)