"""Demiurge layer: strategic decomposition, multi-strategy execution, synthesis."""
from .causal import (
    CausalFinding,
    TraceEvent,
    infer_causes,
)
from .decompose import (
    DecompositionError,
    DecompositionResult,
    SubIntent,
    decompose_intent,
)
from .graph import (
    CycleDetected,
    ExecutionGraph,
    TopologicalSortResult,
    build_graph_from_sub_intents,
)
from .hypotheses import (
    EnsembleResult,
    Hypothesis,
    HypothesisEnsemble,
    score_hypothesis,
)
from .induction import (
    Example,
    Generalization,
    apply_rule,
    induce,
)
from .recall import (
    MemoryAwareDecomposition,
    decompose_with_memory,
)

__all__ = [
    'CausalFinding',
    'CycleDetected',
    'DecompositionError',
    'DecompositionResult',
    'EnsembleResult',
    'Example',
    'ExecutionGraph',
    'Generalization',
    'Hypothesis',
    'HypothesisEnsemble',
    'MemoryAwareDecomposition',
    'SubIntent',
    'TopologicalSortResult',
    'TraceEvent',
    'apply_rule',
    'build_graph_from_sub_intents',
    'decompose_intent',
    'decompose_with_memory',
    'induce',
    'infer_causes',
    'score_hypothesis',
]