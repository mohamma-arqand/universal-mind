"""Demiurge layer: strategic decomposition, multi-strategy execution, synthesis."""
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
    'CycleDetected',
    'DecompositionError',
    'DecompositionResult',
    'ExecutionGraph',
    'ExecutionPlan',
    'ExecutionStrategy',
    'MemoryAwareDecomposition',
    'ParallelStrategy',
    'SequentialStrategy',
    'SpeculativeStrategy',
    'StrategyResult',
    'SubIntent',
    'SynthesisError',
    'SynthesisResult',
    'TopologicalSortResult',
    'build_graph_from_sub_intents',
    'create_n_parallel_strategies',
    'decompose_intent',
    'decompose_with_memory',
    'synthesize_by_sub_intent',
    'synthesize_results',
]