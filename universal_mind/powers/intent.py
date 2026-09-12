"""IntentTranslation power: raw human text → typed Intent.

Spec concept: The ability to translate unstructured human language into
a structured, typed Intent contract with validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..core.intent import Determinism, Intent


@dataclass(frozen=True)
class IntentTranslationInput:
    """Input for intent translation."""
    raw_text: str
    owner_id: str
    context: dict[str, Any] | None = None


@dataclass(frozen=True)
class IntentTranslationOutput:
    """Output from intent translation."""
    intent: Intent
    confidence: float  # 0.0 to 1.0
    extracted_fields: dict[str, Any]
    warnings: list[str]


@runtime_checkable
class IntentTranslation(Protocol):
    """Protocol for translating raw text into structured Intent.

    The IntentTranslation power converts unstructured human requests
    into validated Intent objects with goals, criteria, and constraints.
    """

    async def translate(self, input: IntentTranslationInput) -> IntentTranslationOutput:
        """Translate raw text into a structured Intent.

        Args:
            input: IntentTranslationInput with raw_text, owner_id, context

        Returns:
            IntentTranslationOutput with Intent, confidence, extracted fields
        """
        ...


class InMemoryIntentTranslation:
    """Reference in-memory implementation of IntentTranslation (no I/O).

    Uses simple keyword extraction for demonstration.
    """

    async def translate(self, input: IntentTranslationInput) -> IntentTranslationOutput:
        raw = input.raw_text.strip()
        warnings: list[str] = []
        extracted: dict[str, Any] = {}

        # Very simple extraction for reference implementation
        # In reality this would use NLP/LLM
        words = raw.split()

        # Try to extract a goal (first sentence or first 10 words)
        goal = raw.split('.')[0].strip() if '.' in raw else ' '.join(words[:10])
        extracted['goal'] = goal

        # Extract success criteria (look for "must", "should", "need")
        criteria = []
        for word in ['must', 'should', 'need', 'require']:
            idx = raw.lower().find(word)
            if idx >= 0:
                end = raw.find('.', idx)
                if end < 0:
                    end = len(raw)
                criterion = raw[idx:end].strip()
                criteria.append(criterion)
                extracted.setdefault('criteria', []).append(criterion)

        if not criteria:
            criteria = [f"Complete: {goal}"]
            warnings.append("No explicit success criteria found; using default")

        # Extract constraints (look for "not", "without", "avoid", "limit")
        constraints = []
        for word in ['not', 'without', 'avoid', 'limit', 'cannot', "can't"]:
            idx = raw.lower().find(word)
            if idx >= 0:
                end = raw.find('.', idx)
                if end < 0:
                    end = len(raw)
                constraint = raw[idx:end].strip()
                constraints.append(constraint)
                extracted.setdefault('constraints', []).append(constraint)

        # Determine determinism
        determinism = Determinism.STRICT
        if any(w in raw.lower() for w in ['creative', 'explore', 'brainstorm', 'imagine']):
            determinism = Determinism.CREATIVE

        # A vague/empty request must NOT become a fabricated "Unspecified goal" intent
        # that the rest of the system then treats as a real, actionable commitment.
        # We let IntentIncomplete propagate so the caller decides how to clarify,
        # rather than guessing a placeholder goal on their behalf.
        intent = Intent.from_raw(
            raw_text=raw,
            goal=goal,
            success_criteria=criteria,
            constraints=constraints,
            deadline=None,
            determinism=determinism,
            owner_id=input.owner_id,
        )

        # Confidence based on how much we extracted
        confidence = 0.5
        if len(criteria) > 1:
            confidence += 0.2
        if len(constraints) > 0:
            confidence += 0.2
        if determinism == Determinism.CREATIVE:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        return IntentTranslationOutput(
            intent=intent,
            confidence=confidence,
            extracted_fields=extracted,
            warnings=warnings,
        )