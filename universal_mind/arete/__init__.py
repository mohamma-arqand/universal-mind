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
from universal_mind.arete.counterfactual import (
    CounterfactualError,
    CounterfactualResult,
    counterfactual_check,
)
from universal_mind.arete.cross_judge import (
    CrossJudgeResult,
    cross_judge,
)
from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
    JudgedClaim,
)
from universal_mind.arete.external_evaluator import (
    AuditFinding,
    ExternalAuditResult,
    evaluate_loop,
)
from universal_mind.arete.goal_drift import (
    DriftAssessment,
    assess_goal_drift,
)
from universal_mind.arete.health import (
    JudgmentHealthReport,
    JudgmentHealthSignal,
    assess_judgment_health,
)
from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode
from universal_mind.arete.standard import (
    PromotionDecision,
    PromotionResult,
    Standard,
    StandardKeeper,
    _as_candidate,
)
from universal_mind.arete.uncertainty import (
    EpistemicStatus,
    UncertaintyAssessment,
    assess_uncertainty,
    assess_verdict_uncertainty,
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
    "AuditFinding",
    "CardinalVirtue",
    "CounterfactualError",
    "CounterfactualResult",
    "CrossJudgeResult",
    "Dispute",
    "DriftAssessment",
    "EpistemicStatus",
    "EvidenceBundle",
    "EvidencePoint",
    "EvidenceSource",
    "EvidenceType",
    "ExternalAuditResult",
    "InMemoryArbiter",
    "JudgedClaim",
    "JudgmentHealthReport",
    "JudgmentHealthSignal",
    "JudgmentLineage",
    "JudgmentNode",
    "PromotionDecision",
    "PromotionResult",
    "Standard",
    "StandardKeeper",
    "UncertaintyAssessment",
    "VirtueScorecard",
    "VirtueScorer",
    "VirtueWeights",
    "_as_candidate",
    "assess_goal_drift",
    "assess_judgment_health",
    "assess_uncertainty",
    "assess_verdict_uncertainty",
    "counterfactual_check",
    "cross_judge",
    "default_virtue_scorer",
    "evaluate_loop",
]