"""BoundaryAwareness power: know own limits, emit Refusal or Escalation.

Spec concept: The ability to recognize when a request exceeds the system's
capabilities or safety boundaries, and respond with a structured refusal
or escalation rather than attempting and failing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class BoundaryResponseType(str, Enum):
    """Type of boundary response."""
    REFUSAL = "refusal"      # Cannot do this, here's why
    ESCALATION = "escalation"  # Need human/authority intervention
    DEFERRAL = "deferral"    # Can do later, under different conditions


@dataclass(frozen=True)
class BoundaryRefusal:
    """Structured refusal response."""
    reason: str
    violated_constraint: str
    suggested_alternative: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class BoundaryEscalation:
    """Structured escalation response."""
    reason: str
    required_authority: str
    context: dict[str, Any]
    urgency: str  # "low" | "medium" | "high" | "critical"


@dataclass(frozen=True)
class BoundaryDeferral:
    """Structured deferral response."""
    reason: str
    condition_for_retry: str
    estimated_available: str | None = None


@dataclass(frozen=True)
class BoundaryInput:
    """Input for boundary checking."""
    intent: Any  # Intent object
    requested_capability: str | None = None
    context: dict[str, Any] | None = None


@dataclass(frozen=True)
class BoundaryOutput:
    """Output from boundary check."""
    allowed: bool
    response_type: BoundaryResponseType | None = None
    refusal: BoundaryRefusal | None = None
    escalation: BoundaryEscalation | None = None
    deferral: BoundaryDeferral | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class BoundaryAwareness(Protocol):
    """Protocol for knowing own limits and emitting refusals/escalations.

    The BoundaryAwareness power evaluates whether a request is within
    the system's operational and safety boundaries, returning structured
    responses for out-of-bounds requests.
    """

    async def check(self, input: BoundaryInput) -> BoundaryOutput:
        """Check if request is within boundaries.

        Args:
            input: BoundaryInput with intent, requested_capability, context

        Returns:
            BoundaryOutput with allowed flag and structured response if not
        """
        ...


class InMemoryBoundaryAwareness:
    """Reference in-memory implementation of BoundaryAwareness (no I/O)."""

    def __init__(
        self,
        allowed_domains: frozenset[str] | None = None,
        max_cost: float = 1000.0,
        require_human_for: frozenset[str] | None = None,
    ) -> None:
        self._allowed_domains = allowed_domains or frozenset(["general", "compute", "analysis"])
        self._max_cost = max_cost
        self._require_human_for = require_human_for or frozenset(["destructive", "financial", "security"])

    async def check(self, input: BoundaryInput) -> BoundaryOutput:
        intent = input.intent
        context = input.context or {}

        # Check domain
        intent_domain = getattr(intent, 'goal', '').lower()
        domain_allowed = any(d in intent_domain for d in self._allowed_domains)

        if not domain_allowed:
            return BoundaryOutput(
                allowed=False,
                response_type=BoundaryResponseType.REFUSAL,
                refusal=BoundaryRefusal(
                    reason=f"Domain not in allowed list: {self._allowed_domains}",
                    violated_constraint="domain_allowlist",
                    suggested_alternative="Rephrase request to fit allowed domains",
                ),
            )

        # Check cost (if present in context)
        estimated_cost = context.get('estimated_cost', 0.0)
        if estimated_cost > self._max_cost:
            return BoundaryOutput(
                allowed=False,
                response_type=BoundaryResponseType.ESCALATION,
                escalation=BoundaryEscalation(
                    reason=f"Estimated cost {estimated_cost} exceeds limit {self._max_cost}",
                    required_authority="budget_approver",
                    context={"estimated_cost": estimated_cost, "max_cost": self._max_cost},
                    urgency="medium",
                ),
            )

        # Check for human-required capabilities
        capability = input.requested_capability or ""
        if any(req in capability.lower() for req in self._require_human_for):
            return BoundaryOutput(
                allowed=False,
                response_type=BoundaryResponseType.ESCALATION,
                escalation=BoundaryEscalation(
                    reason=f"Capability {capability} requires human authorization",
                    required_authority="human_operator",
                    context={"capability": capability, "intent_goal": getattr(intent, 'goal', '')},
                    urgency="high",
                ),
            )

        return BoundaryOutput(
            allowed=True,
            metadata={"domain_checked": True, "cost_checked": True},
        )