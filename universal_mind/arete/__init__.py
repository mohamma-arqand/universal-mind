"""ARETĒ arbitration — virtue-based adjudication of competing candidates.

ARETĒ (ἀρετή, "excellence"/"virtue") settles disputes between competing
candidate outputs using a non-compensatory cardinal-virtue rubric: a candidate
that violates a hard-gate virtue (Justice by default) is disqualified no matter
how high its overall excellence ranks.
"""

from __future__ import annotations

from universal_mind.arete.arbiter import (
    ArbitrationVerdict,
    Arbitrator,
    Dispute,
    InMemoryArbiter,
    VirtueScorecard,
    VirtueScorer,
    default_virtue_scorer,
)
from universal_mind.arete.virtue import (
    AreteError,
    CardinalVirtue,
    VirtueWeights,
)

__all__ = [
    "ArbitrationVerdict",
    "Arbitrator",
    "AreteError",
    "CardinalVirtue",
    "Dispute",
    "InMemoryArbiter",
    "VirtueScorecard",
    "VirtueScorer",
    "VirtueWeights",
    "default_virtue_scorer",
]