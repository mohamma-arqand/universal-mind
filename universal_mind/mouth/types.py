"""MOUTH data models — typed commitments and the errors the input gate raises.

These are kept in their own module so :mod:`universal_mind.mouth.commit` can
import them without a circular import back through the package ``__init__``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from universal_mind.arete.evidence import EvidenceBundle
from universal_mind.core.errors import CallerFault
from universal_mind.core.intent import Intent


class MouthError(CallerFault):
    """Base exception for MOUTH input-gate failures."""


class IntentNeedsClarification(MouthError):
    """The raw request is too vague/incomplete to commit to; a question is needed.

    Caller fault: raising this does NOT record an execution fault and does not
    trip the error-rate throttle — a vague request is the caller's to fix.
    """

    def __init__(self, questions: list[str]) -> None:
        self.questions = list(questions)
        super().__init__(
            "The request is not specific enough to commit to. Clarify: "
            + "; ".join(questions)
        )


class IntentConflict(MouthError):
    """The raw request contradicts itself and cannot be committed as-is."""

    def __init__(self, conflict: str) -> None:
        self.conflict = conflict
        super().__init__(f"Intent conflict: {conflict}")


@dataclass(frozen=True)
class CommitEvidence:
    """Proof of where a committed field came from in the raw text."""

    field: str
    source_span: str
    evidence: EvidenceBundle


@dataclass(frozen=True)
class StructuredIntent:
    """A typed commitment the MOUTH layer hands to the orchestrator.

    Wraps a validated :class:`~universal_mind.core.intent.Intent` and binds each
    committed field to an :class:`EvidenceBundle` so the commitment is evidence-
    anchored, not asserted. ``questions`` lists clarifications the mouth asked
    (empty when the commitment is complete).
    """

    intent: Intent
    field_evidence: dict[str, EvidenceBundle] = field(default_factory=dict)
    questions_asked: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """JSON-safe payload including per-field evidence, for the ledger."""
        return {
            "intent": self.intent.to_payload(),
            "field_evidence": {
                field: [p.citation for p in bundle.points]
                for field, bundle in self.field_evidence.items()
            },
            "questions_asked": list(self.questions_asked),
        }