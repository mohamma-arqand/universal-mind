"""Capability adapter boundary used by the Executive Mind."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..core.errors import CallerFault
from ..core.intent import Determinism, Intent


class ContractViolation(CallerFault):
    """Raised when an intent violates capability contract requirements.
    
    This is a caller fault - non-retryable and excluded from error-rate throttling.
    """


@dataclass(frozen=True)
class CapabilityResult:
    """Immutable result returned by a capability execution."""

    ok: bool
    output: Any
    cost: dict[str, Any]
    provenance: dict[str, Any]
    notes: tuple[str, ...] = ()


class Capability(ABC):
    """Abstract capability executable by the Executive Mind."""

    def validate_intent(self, intent: Intent) -> None:
        """Validate that the intent conforms to capability contract requirements.
        
        Override in subclasses to add custom validation logic.
        Raises ContractViolation if validation fails.
        """

    @abstractmethod
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        """Execute the capability for a validated intent."""


class EchoCapability(Capability):
    """Trivial built-in capability that echoes intent and params."""

    def validate_intent(self, intent: Intent) -> None:
        """Validate that the intent has valid determinism and no deadline violations."""
        if intent.determinism not in (Determinism.STRICT, Determinism.CREATIVE):
            raise ContractViolation(f"Invalid determinism level: {intent.determinism}")
        if intent.deadline is not None:
            from datetime import datetime, timezone
            if intent.deadline < datetime.now(timezone.utc):
                raise ContractViolation("Intent deadline is in the past")

    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        return CapabilityResult(
            ok=True,
            output={
                'goal': intent.goal,
                'raw_text': intent.raw_text,
                'params': dict(params),
            },
            cost={'currency': 'cycles', 'amount': 1},
            provenance={'producer': 'EchoCapability'},
            notes=('echoed',),
        )
