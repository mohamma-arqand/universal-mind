"""Human-in-the-loop consent for ARETĒ promotions.

The charter forbids majority voting and demands *judgment backed by evidence*;
the human verdict is the highest-trust evidence source (:class:`EvidenceSource.HUMAN`).
This module makes that concrete at the only place the system self-modifies its
own standard: a promotion is **provisional** until a human consents or vetoes it,
and the consent/veto is committed to the ledger as a first-class
:class:`EvidenceType.CONSENT` point — never a silent override, never a bare vote.

In a deterministic, local setting the consent source is injectable: the default
is *not* consenting (a promotion stays tentative), which is the safe posture.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)
from universal_mind.arete.standard import PromotionDecision, StandardKeeper
from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.powers.judgment import CandidateOutput


class HumanVerdict(str, Enum):
    """A human's ruling on a provisional promotion."""

    CONSENT = "consent"
    VETO = "veto"


@dataclass(frozen=True)
class ConsentOutcome:
    """Result of applying (or withholding) human consent on a promotion."""

    promotion_decision: PromotionDecision
    human_verdict: HumanVerdict
    finalized: bool            # True once a human ruling is recorded
    record_id: str
    evidence: EvidenceBundle


# A consent source answers "does a human consent to this promotion?".
# The default is conservative: no implicit consent (everything stays tentative).
ConsentSource = Callable[[CandidateOutput, StandardKeeper], HumanVerdict]


def _default_consent(proposal: CandidateOutput, keeper: StandardKeeper) -> HumanVerdict:
    """Reference consent: deny-by-default (a human must explicitly consent)."""
    return HumanVerdict.VETO


class PromotionConsent:
    """Wraps a StandardKeeper so promotions require human consent to finalize.

    It does NOT bypass ARETĒ: the keeper's non-compensatory arbitration still
    decides *promoted vs deferred/rejected*. This layer only adds the human
    ruling on top — a promotion the arbitrator already ALLOWed becomes final
    only when the (injected) human gives consent, and the ruling is committed
    to the ledger as CONSENT evidence.
    """

    def __init__(
        self,
        keeper: StandardKeeper,
        *,
        consent: ConsentSource | None = None,
        clock: Clock | None = None,
        owner: Identity = DEFAULT_OWNER,
    ) -> None:
        self._keeper = keeper
        self._consent = consent if consent is not None else _default_consent
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner
        self._mnemosyne = Mnemosyne(keeper.store, self._clock)

    def consider(self, proposal: CandidateOutput) -> ConsentOutcome:
        """Arbitrate via the keeper, then gate any promotion on human consent."""
        promotion = self._keeper.consider(proposal)
        verdict = self._consent(proposal, self._keeper)
        record_id = self._mnemosyne.record(
            owner_id=self._owner.owner_id,
            kind="human_consent",
            payload={
                "promotion_decision": promotion.decision.value,
                "contender": proposal.strategy_id,
                "verdict": verdict.value,
            },
            provenance={"producer": "PromotionConsent", "owner_id": self._owner.owner_id},
        )
        evidence = EvidenceBundle(
            (
                EvidencePoint(
                    type_=EvidenceType.CONSENT,
                    source=EvidenceSource.HUMAN,
                    value=verdict.value,
                    citation=f"human-consent:{proposal.strategy_id}",
                    weight=3.0,  # the highest-trust source
                ),
            )
        )
        finalized = promotion.decision is PromotionDecision.PROMOTED and verdict is HumanVerdict.CONSENT
        return ConsentOutcome(
            promotion_decision=promotion.decision,
            human_verdict=verdict,
            finalized=finalized,
            record_id=record_id,
            evidence=evidence,
        )