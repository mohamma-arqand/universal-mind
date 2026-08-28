"""Intent contract turning raw text into a structured commitment."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .errors import CallerFault


class Determinism(str, Enum):
    """Intent determinism level."""

    STRICT = 'strict'
    CREATIVE = 'creative'


class IntentIncomplete(CallerFault):
    """Raised when a raw request lacks a usable goal or criteria.

    A caller fault: the caller supplied an invalid/incomplete intent. It is
    non-retryable and excluded from error-rate throttling.
    """


@dataclass(frozen=True)
class Intent:
    """Structured commitment derived from a human request."""

    raw_text: str
    goal: str
    success_criteria: list[str]
    constraints: list[str]
    deadline: datetime | None
    determinism: Determinism
    owner_id: str

    @classmethod
    def from_raw(
        cls,
        *,
        raw_text: str,
        goal: str,
        success_criteria: list[str],
        constraints: list[str] | None = None,
        deadline: datetime | None = None,
        determinism: Determinism = Determinism.STRICT,
        owner_id: str,
    ) -> 'Intent':
        """Validate required fields and build an Intent."""
        if not goal or not goal.strip() or not success_criteria:
            raise IntentIncomplete('Intent requires a goal and at least one success criterion.')
        return cls(
            raw_text=raw_text,
            goal=goal.strip(),
            success_criteria=[item for item in success_criteria if item and item.strip()],
            constraints=[item for item in (constraints or []) if item and item.strip()],
            deadline=deadline,
            determinism=determinism,
            owner_id=owner_id,
        )

    def to_payload(self) -> dict[str, Any]:
        """Convert the intent to a JSON-serializable payload."""
        return {
            'raw_text': self.raw_text,
            'goal': self.goal,
            'success_criteria': list(self.success_criteria),
            'constraints': list(self.constraints),
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'determinism': self.determinism.value,
            'owner_id': self.owner_id,
        }

    def assert_complete(self) -> None:
        """Enforce that the intent is fully contract-complete.

        Ensures all required contract fields are present and valid.
        Raises IntentIncomplete if any required contract element is missing.
        """
        if not self.goal or not self.goal.strip():
            raise IntentIncomplete('Intent goal is required.')
        if len(self.success_criteria) == 0:
            raise IntentIncomplete('Intent requires at least one success criterion.')
        if not any(c and c.strip() for c in self.success_criteria):
            raise IntentIncomplete('Intent requires at least one non-empty success criterion.')
        if not self.owner_id:
            raise IntentIncomplete('Intent requires a valid owner_id.')
        if self.determinism not in (Determinism.STRICT, Determinism.CREATIVE):
            raise IntentIncomplete(f'Invalid determinism level: {self.determinism!r}.')

    def validates_params(self, params: dict[str, Any]) -> None:
        """Enforce that the provided execution params satisfy the intent contract.

        Raises IntentIncomplete if required params are missing.
        """
        required = {'owner_id'}
        missing = required - set(params)
        if missing:
            raise IntentIncomplete(f'Missing required execution params: {sorted(missing)}.')
