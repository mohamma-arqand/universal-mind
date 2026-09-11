"""Powers package: the fundamental powers of universal_mind.

Each power is a Protocol with a reference in-memory implementation.
"""
from __future__ import annotations

from .boundary import (
    BoundaryAwareness,
    BoundaryDeferral,
    BoundaryEscalation,
    BoundaryInput,
    BoundaryOutput,
    BoundaryRefusal,
    BoundaryResponseType,
    InMemoryBoundaryAwareness,
)
from .intent import (
    InMemoryIntentTranslation,
    IntentTranslation,
    IntentTranslationInput,
    IntentTranslationOutput,
)
from .introspection_feedback import (
    GenerationInsight,
    extract_insights,
    make_insight_driven_generator,
    shaped_description,
)
from .judgment import (
    CandidateOutput,
    InMemoryJudgment,
    Judgment,
    JudgmentInput,
    JudgmentOutput,
    Verdict,
)
from .summon import InMemorySummon, Summon, SummonInput, SummonOutput

__all__ = [
    "BoundaryAwareness",
    "BoundaryDeferral",
    "BoundaryEscalation",
    "BoundaryInput",
    "BoundaryOutput",
    "BoundaryRefusal",
    "BoundaryResponseType",
    "CandidateOutput",
    "GenerationInsight",
    "InMemoryBoundaryAwareness",
    "InMemoryIntentTranslation",
    "InMemoryJudgment",
    "InMemorySummon",
    "IntentTranslation",
    "IntentTranslationInput",
    "IntentTranslationOutput",
    "Judgment",
    "JudgmentInput",
    "JudgmentOutput",
    "Summon",
    "SummonInput",
    "SummonOutput",
    "Verdict",
    "extract_insights",
    "make_insight_driven_generator",
    "shaped_description",
]