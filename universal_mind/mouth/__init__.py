"""MOUTH — the sole user interface and the place raw speech becomes commitment.

The governing architecture says the system has ONE identity and ONE point of
interaction (L6 MOUTH), and that a vague request handed to hundreds of
specialists is the single biggest failure mode of a synthetic system. MOUTH's
job is therefore *before* orchestration: turn ambiguous raw text into a
:class:`StructuredIntent` — a typed, evidence-anchored commitment — or
explicitly refuse with a clarification request rather than silently proceed on
something incomplete.

A :class:`StructuredIntent` is not just a re-labeled ``Intent``: it carries an
:class:`~universal_mind.arete.evidence.EvidenceBundle` recording *where* each
field came from in the raw text, so the commitment is auditable — the same
"judgment backed by evidence" discipline applied to the input gate.
"""

from __future__ import annotations

from universal_mind.mouth.commit import (
    ConscientiousMouth,
    GuardedMouth,
    InMemoryMouth,
    Mouth,
)
from universal_mind.mouth.types import (
    CommitEvidence,
    IntentConflict,
    IntentNeedsClarification,
    MouthError,
    StructuredIntent,
)

__all__ = [
    "CommitEvidence",
    "ConscientiousMouth",
    "GuardedMouth",
    "InMemoryMouth",
    "IntentConflict",
    "IntentNeedsClarification",
    "Mouth",
    "MouthError",
    "StructuredIntent",
]