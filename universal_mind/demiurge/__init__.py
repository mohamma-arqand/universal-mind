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
from .strategies import (
    ExecutionPlan,
    ExecutionStrategy,
    ParallelStrategy,
    SequentialStrategy,
    SpeculativeStrategy,
    StrategyResult,
    create_n_parallel_strategies,
)
from .synthesis import (
    SynthesisError,
    SynthesisResult,
    synthesize_by_sub_intent,
    synthesize_results,
)

__all__ = [
    'CausalFinding',
    'CycleDetected',
    'DecompositionError',
    'DecompositionResult',
    'EnsembleResult',
    'Example',
    'ExecutionGraph',
    'ExecutionPlan',
    'ExecutionStrategy',
    'Generalization',
    'Hypothesis',
    'HypothesisEnsemble',
    'MemoryAwareDecomposition',
    'ParallelStrategy',
    'SequentialStrategy',
    'SpeculativeStrategy',
    'StrategyResult',
    'SubIntent',
    'SynthesisError',
    'SynthesisResult',
    'TopologicalSortResult',
    'TraceEvent',
    'apply_rule',
    'build_graph_from_sub_intents',
    'create_n_parallel_strategies',
    'decompose_intent',
    'decompose_with_memory',
    'induce',
    'infer_causes',
    'score_hypothesis',
    'synthesize_by_sub_intent',
    'synthesize_results',
]