"""Powers package: the seven fundamental powers of universal_mind.

Each power is a Protocol with a reference in-memory implementation.
"""
from __future__ import annotations

from .accretion import (
    AccretionInput,
    AccretionOutput,
    AccretiveMemory,
    Experience,
    InMemoryAccretiveMemory,
    Lesson,
)
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
from .devour import Devour, DevourInput, DevourOutput, InMemoryDevour, ToolDescriptor
from .hand import Hand, HandInput, HandOutput, InMemoryHand
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
    "AccretionInput",
    "AccretionOutput",
    "AccretiveMemory",
    "BoundaryAwareness",
    "BoundaryDeferral",
    "BoundaryEscalation",
    "BoundaryInput",
    "BoundaryOutput",
    "BoundaryRefusal",
    "BoundaryResponseType",
    "CandidateOutput",
    "Devour",
    "DevourInput",
    "DevourOutput",
    "Experience",
    "GenerationInsight",
    "Hand",
    "HandInput",
    "HandOutput",
    "InMemoryAccretiveMemory",
    "InMemoryBoundaryAwareness",
    "InMemoryDevour",
    "InMemoryHand",
    "InMemoryIntentTranslation",
    "InMemoryJudgment",
    "InMemorySummon",
    "IntentTranslation",
    "IntentTranslationInput",
    "IntentTranslationOutput",
    "Judgment",
    "JudgmentInput",
    "JudgmentOutput",
    "Lesson",
    "Summon",
    "SummonInput",
    "SummonOutput",
    "ToolDescriptor",
    "Verdict",
    "extract_insights",
    "make_insight_driven_generator",
    "shaped_description",
]