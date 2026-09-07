"""ARETĒ arbitration — virtue-based adjudication of competing candidates.

ARETĒ (ἀρετή, "excellence"/"virtue") is the arbitration layer that settles
disputes between competing candidate outputs using a cardinal-virtue rubric.
It is deliberately **non-compensatory**: a candidate that falls below a
hard-gate virtue (Justice by default) is disqualified no matter how high its
overall score ranks. Remaining candidates compete on weighted excellence.

This module defines the virtue model and its validation. The decision engine
lives in :mod:`universal_mind.arete.arbiter`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from universal_mind.core.errors import UniversalMindError


class CardinalVirtue(str, Enum):
    """The four cardinal virtues used as the arbitration rubric.

    Values are stable lowercase slugs; the Enum is also a ``str`` so it can be
    used directly as a key in JSON-ish metadata.
    """

    WISDOM = "wisdom"  # phronesis — sound knowledge and judgment
    COURAGE = "courage"  # andreia — honesty and accountability
    TEMPERANCE = "temperance"  # sophrosune — restraint and measure
    JUSTICE = "justice"  # dikaiosune — fairness, rights, consent


class AreteError(UniversalMindError):
    """Raised for invalid ARETĒ configuration or malformed disputes."""


def _default_weights() -> dict[CardinalVirtue, float]:
    """Equal unit weights over the four cardinal virtues."""
    return {virtue: 1.0 for virtue in CardinalVirtue}


def _default_hard_gate() -> frozenset[CardinalVirtue]:
    """Justice is the only hard gate by default: unfairness never compensates."""
    return frozenset({CardinalVirtue.JUSTICE})


@dataclass(frozen=True)
class VirtueWeights:
    """Configuration for virtue-based arbitration.

    Attributes:
        weights: Per-virtue relative weight. Must cover every cardinal virtue
            with a non-negative value and at least one strictly positive value.
        hard_gate: Virtues whose violation (score below ``hard_gate_threshold``)
            disqualifies a candidate regardless of overall excellence.
        hard_gate_threshold: Minimum score on each hard-gate virtue.
        accept_threshold: Minimum weighted excellence for an arbitrator to
            ratify (ALLOW) the best qualified candidate.
        tie_epsilon: Absolute float tolerance under which the top two
            excellence scores are considered a tie (ruled DEFER).
    """

    weights: dict[CardinalVirtue, float] = field(default_factory=_default_weights)
    hard_gate: frozenset[CardinalVirtue] = field(default_factory=_default_hard_gate)
    hard_gate_threshold: float = 0.4
    accept_threshold: float = 0.5
    tie_epsilon: float = 1e-9

    def __post_init__(self) -> None:
        """Validate the configuration against the cardinal-virtue model."""
        missing = [v for v in CardinalVirtue if v not in self.weights]
        if missing:
            raise AreteError(
                "VirtueWeights must cover every cardinal virtue; missing: "
                + ", ".join(v.value for v in missing)
            )
        if any(w < 0 for w in self.weights.values()):
            raise AreteError("Virtue weights must be non-negative")
        if not any(w > 0 for w in self.weights.values()):
            raise AreteError("At least one virtue weight must be strictly positive")
        # Ensure the hard gate is a subset of the modelled virtues.
        unknown = self.hard_gate - set(CardinalVirtue)
        if unknown:
            raise AreteError(
                "Hard-gate virtues must be cardinal virtues; unknown: "
                + ", ".join(v.value for v in unknown)
            )
        if not 0.0 <= self.hard_gate_threshold <= 1.0:
            raise AreteError("hard_gate_threshold must be in [0.0, 1.0]")
        if not 0.0 <= self.accept_threshold <= 1.0:
            raise AreteError("accept_threshold must be in [0.0, 1.0]")

    def total_weight(self) -> float:
        """Sum of the configured virtue weights (always > 0 after validation)."""
        return sum(self.weights.values())