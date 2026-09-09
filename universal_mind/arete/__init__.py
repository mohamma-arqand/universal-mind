"""ARETĒ arbitration — evidence-backed adjudication of competing candidates.

ARETĒ (ἀρετή, "excellence") settles disputes between competing candidate
outputs using a non-compensatory cardinal-virtue rubric: a candidate that
violates a hard-gate virtue (Justice by default) is disqualified no matter how
high its overall excellence ranks.

Every verdict carries a mandatory :class:`EvidenceBundle` (see
:mod:`universal_mind.arete.evidence`) — judgment is anchored to inspectable
evidence, never to a bare score or a majority vote.
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
from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
    JudgedClaim,
)
from universal_mind.arete.standard import (
    PromotionDecision,
    PromotionResult,
    Standard,
    StandardKeeper,
    _as_candidate,
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
    "EvidenceBundle",
    "EvidencePoint",
    "EvidenceSource",
    "EvidenceType",
    "InMemoryArbiter",
    "JudgedClaim",
    "PromotionDecision",
    "PromotionResult",
    "Standard",
    "StandardKeeper",
    "VirtueScorecard",
    "VirtueScorer",
    "VirtueWeights",
    "_as_candidate",
    "default_virtue_scorer",
]