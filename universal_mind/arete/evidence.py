"""ARETĒ evidence — the audit substrate of judgment.

The governing rule forbids simple majority voting and demands *judgment backed
by evidence*. This module makes evidence a first-class, inspectable object:
every judgment a judge asserts is anchored to at least one
:class:`EvidencePoint` carrying a source, a type, a value, and a citation. A
verdict that cannot show its evidence is, by construction, unrepresentable
here — so "because I said so" is impossible to emit.

Evidence is also how ARETĒ connects to the human-feedback channel: a human
"rejected" verdict is a first-class evidence point with the highest source
weight, not a side note.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceSource(str, Enum):
    """Who or what produced a piece of evidence."""

    HUMAN = "human"            # first-class: a human verdict/observation
    MEASUREMENT = "measurement"  # a computed metric (error rate, latency, cost)
    TEST = "test"               # a benchmark/probe/pytest result
    PROVIDER = "provider"       # a provider self-report (lowest trust)
    LEDGER = "ledger"           # a record already committed to the ledger


class EvidenceType(str, Enum):
    """What kind of claim the evidence supports."""

    CORRECTNESS = "correctness"
    SAFETY = "safety"
    REVERSIBILITY = "reversibility"
    COST = "cost"
    LATENCY = "latency"
    RELIABILITY = "reliability"
    CONSENT = "consent"        # human approval/veto
    REGRESSION = "regression"  # a change got worse (for accept/reject)


@dataclass(frozen=True)
class EvidencePoint:
    """One inspectable fact underpinning a judgment.

    Attributes:
        type_: What the evidence supports (see :class:`EvidenceType`).
        source: Where it came from (see :class:`EvidenceSource`).
        value: The measured/observed value (float, bool, string, or nested).
        citation: A stable, human-readable pointer to where this came from
            (a test name, a ledger record id, a probe name, a metric name).
        weight: Relative trust in this point (higher is more trusted; the
            default 1.0 means "ordinary evidence").
    """

    type_: EvidenceType
    source: EvidenceSource
    value: Any
    citation: str
    weight: float = 1.0


@dataclass(frozen=True)
class EvidenceBundle:
    """A set of evidence points a judgment rests on (never empty).

    Invariant (enforced in :meth:`__post_init__`): a bundle must carry at least
    one evidence point — an unevidenced judgment is unrepresentable.
    """

    points: tuple[EvidencePoint, ...]

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("EvidenceBundle must contain at least one EvidencePoint")

    def total_weight(self) -> float:
        """Sum of the weights of all points (always > 0)."""
        return sum(p.weight for p in self.points)

    def strongest(self) -> EvidencePoint:
        """The single most-trusted point in the bundle."""
        return max(self.points, key=lambda p: p.weight)

    def by_source(self, source: EvidenceSource) -> tuple[EvidencePoint, ...]:
        """Points originating from ``source``."""
        return tuple(p for p in self.points if p.source == source)

    def has_human(self) -> bool:
        """True if any point came from a human (the highest-trust source)."""
        return any(p.source == EvidenceSource.HUMAN for p in self.points)

    def describe(self) -> list[str]:
        """Human-readable citations, one per point."""
        return [f"[{p.source.value}:{p.type_.value}] {p.citation} = {p.value}" for p in self.points]


# A judgment is a decision paired with the evidence that justifies it.
@dataclass(frozen=True)
class JudgedClaim:
    """A single asserted judgment and the evidence that anchors it."""

    claim: str
    evidence: EvidenceBundle
    conclusion: Any = field(default=None)