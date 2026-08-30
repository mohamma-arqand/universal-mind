"""Gates package: unified gate evaluation pipeline.

This package provides a single, authoritative gate evaluation pipeline that
replaces the previous dual-pipeline architecture (CompositeStrategicGate in
executive.py + PrecedencePipeline in gates/precedence.py).

Exports:
- Gate protocol and base classes
- PrecedencePipeline: deterministic ordering by (precedence, name)
- PowerZero: absolute veto authority gate
- LayeringGate: enforces layer boundaries
"""

from .base import Gate, GateResult, Verdict, combine_verdicts
from .layering import (
    LayeringGate,
    LayerViolation,
    create_layering_gate,
    get_layer,
    is_foundation,
)
from .power_zero import (
    AlwaysVetoPowerZero,
    ConditionalVetoPowerZero,
    DefaultPowerZero,
    PowerZero,
)
from .precedence import PipelineJudgment, PrecedencePipeline, create_default_pipeline

__all__ = [
    "AlwaysVetoPowerZero",
    "ConditionalVetoPowerZero",
    "DefaultPowerZero",
    "Gate",
    "GateResult",
    "LayerViolation",
    "LayeringGate",
    "PipelineJudgment",
    "PowerZero",
    "PrecedencePipeline",
    "Verdict",
    "combine_verdicts",
    "create_default_pipeline",
    "create_layering_gate",
    "get_layer",
    "is_foundation",
]