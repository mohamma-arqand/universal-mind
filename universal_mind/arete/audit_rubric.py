"""External audit rubric — a fixed, versioned, neutral yardstick.

Self-assessment always under-samples its own blind spots. This module is the
*counter*: a fixed, versioned rubric that a neutral party applies to score how
"global" the system genuinely is, without trusting the system's self-report. The
dimensions are orthogonal to the mind's own signals — verifiable from the outside:
test count, probe count, type-cleanliness, an adversarial red-team pass, and a
counterfactual robustness sample.

The rubric is immutable (its version is part of its identity), so a scorecard
can always say *which* yardstick produced it — an auditable judgment, not a
self-flattering number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RubricDimension:
    """One scoring dimension: name, weight, and a verifiable measurement."""

    name: str
    weight: float
    value: float        # 0..1 measurement
    evidence: str       # what / where this measurement came from


@dataclass(frozen=True)
class AuditScorecard:
    """The neutral audit result for one versioned rubric."""

    rubric_version: str
    dimensions: tuple[RubricDimension, ...]
    score: float                     # 0..1 weighted score
    verdict: str                     # honest human-readable reading
    evidence: dict[str, Any]         # the raw measurements backing the score


class ExternalRubric:
    """A fixed, versioned rubric applied by a neutral party."""

    def __init__(self, version: str = "1.0.0") -> None:
        self._version = version

    @property
    def version(self) -> str:
        return self._version

    def score(self, measurements: dict[str, Any]) -> AuditScorecard:
        """Score the system against the rubric from *external* measurements.

        ``measurements`` must come from outside the system's self-report — e.g.
        an independent test run, a separate probe runner, a type checker. The
        rubric maps them to weighted dimensions and returns an honest scorecard
        (never a guaranteed pass).
        """
        dims = [
            RubricDimension(
                name="tests_green",
                weight=0.25,
                value=1.0 if measurements.get("tests_failures", 0) == 0 else 0.0,
                evidence=f"independent pytest run, failures={measurements.get('tests_failures', '?')}",
            ),
            RubricDimension(
                name="probes_green",
                weight=0.25,
                value=1.0 if measurements.get("probes_failed", 0) == 0 else 0.0,
                evidence=f"independent probe run, failed={measurements.get('probes_failed', '?')}",
            ),
            RubricDimension(
                name="type_clean",
                weight=0.2,
                value=1.0 if measurements.get("mypy_errors", 1) == 0 else 0.0,
                evidence=f"mypy errors={measurements.get('mypy_errors', '?')}",
            ),
            RubricDimension(
                name="red_team_blocked",
                weight=0.15,
                value=1.0 if measurements.get("red_team_penetrated", 1) == 0 else 0.0,
                evidence=f"adversarial sweep penetrated={measurements.get('red_team_penetrated', '?')}",
            ),
            RubricDimension(
                name="counterfactual_robust",
                weight=0.15,
                value=float(measurements.get("robust_fraction", 0.0)),
                evidence=f"robust-fraction={measurements.get('robust_fraction', '?')}",
            ),
        ]

        total_weight = sum(d.weight for d in dims)
        score = sum(d.weight * d.value for d in dims) / total_weight if total_weight else 0.0

        verdict = _read_score(score)
        return AuditScorecard(
            rubric_version=self._version,
            dimensions=tuple(dims),
            score=round(score, 4),
            verdict=verdict,
            evidence=measurements,
        )


def _read_score(score: float) -> str:
    """Translate a 0..1 score into an honest plain-language reading."""
    if score >= 0.9:
        return "genuinely strong — the yardstick is not flattering, this holds up"
    if score >= 0.7:
        return "solid with known gaps — worth publishing, mark the gaps clearly"
    if score >= 0.5:
        return "promising but incomplete — do not claim 'beyond world class' yet"
    return "not yet auditable worldwide — the gaps are real and visible"