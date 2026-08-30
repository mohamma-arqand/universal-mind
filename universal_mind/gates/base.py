"""Gate protocol and base classes for the unified pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class Verdict(Enum):
    """Gate evaluation verdict."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"


@dataclass(frozen=True)
class GateResult:
    """Result of a single gate evaluation."""
    gate_name: str
    precedence: int
    verdict: Verdict
    reason: str
    skipped: bool = False
    skip_reason: str | None = None


class Gate(Protocol):
    """Protocol for all gates in the pipeline.

    Each gate must declare a stable integer precedence (higher = runs first)
    and a unique name. Gates are ordered by (-precedence, name) for
    deterministic tie-breaking.
    """

    @property
    def precedence(self) -> int:
        """Stable integer precedence. Higher runs first."""
        ...

    @property
    def name(self) -> str:
        """Unique gate name for tie-breaking and tracing."""
        ...

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        """Evaluate the gate against the context.

        Context keys available:
        - 'intent': Intent being evaluated
        - 'capability': CapabilityDossier being targeted
        - 'risk_level': str (if assessed)
        - Any other keys added by earlier gates

        Returns:
            Verdict.ALLOW: proceed to next gate
            Verdict.DENY: hard stop, execution blocked
            Verdict.DEFER: soft stop, execution deferred
        """
        ...


def combine_verdicts(verdicts: list[Verdict]) -> Verdict:
    """Combine verdicts from all gates.

    Rules (fail-closed):
    - One DENY = DENY (highest priority)
    - DEFER beats ALLOW (if no DENY)
    - All ALLOW = ALLOW

    Note: PowerZero veto (DENY at highest precedence) short-circuits
    before this function is called.
    """
    if Verdict.DENY in verdicts:
        return Verdict.DENY
    if Verdict.DEFER in verdicts:
        return Verdict.DEFER
    return Verdict.ALLOW