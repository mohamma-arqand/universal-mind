"""ARETĒ critical loop — promote a synthesized D to the standing standard.

The governing rule (the "judgment" half of ONE INTEGRATED JUDGMENT): a
proposed artifact D only becomes the normative standard when an ARETĒ
arbitration explicitly rules it better than the current standard. If the
arbitrator says so, D is promoted and persisted to the ledger as the new
standard; if it declines or defers, the current standard survives unshaken.
Merit is earned by evidence, never by identity or recency.

Deterministic and local: arbitration is the non-compensatory rule from
:mod:`arete.arbiter`, and the standard's ledger history is append-only, so the
track of promotions is auditable and replayable. No external provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore
from universal_mind.powers.judgment import CandidateOutput, Verdict

from .arbiter import (
    ArbitrationVerdict,
    Dispute,
    InMemoryArbiter,
    VirtueScorer,
)
from .evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)
from .virtue import VirtueWeights


class PromotionDecision(str, Enum):
    """Outcome of a critical-loop proposal against the standing standard."""

    PROMOTED = "promoted"    # arbitrator ALLOWed the proposal over the standard
    REJECTED = "rejected"    # arbitrator ruled the proposal worse/equivalent
    DEFERRED = "deferred"    # arbitration was not decisive (tie / under threshold)


@dataclass(frozen=True)
class Standard:
    """A canonical artifact currently held as the standard."""

    name: str
    artifact: object
    promotion_depth: int = 0      # how many generations onto this lineage
    evidence: EvidenceBundle | None = None


@dataclass(frozen=True)
class PromotionResult:
    """Outcome of one critical-loop proposal, fully anchored in evidence."""

    decision: PromotionDecision
    contender: CandidateOutput
    previous_standard: Standard | None
    current_standard: Standard
    verdict: ArbitrationVerdict | None = None
    record_id: str | None = None


def _seed_bundle(reason: str, winner: str) -> EvidenceBundle:
    """A minimal, valid evidence bundle anchoring a decision."""
    return EvidenceBundle(
        (
            EvidencePoint(
                type_=EvidenceType.CORRECTNESS,
                source=EvidenceSource.TEST,
                value=True,
                citation=f"promotion:{winner}:{reason}",
            ),
        )
    )


def _as_candidate(standard: Standard) -> CandidateOutput:
    """Present a Standard as a competing candidate in a dispute.

    The incumbent standard is scored as strong but *improvable* (wisdom 0.9, not
    1.0): it earned its place on past evidence, so a contender that arrives with
    strictly better, fully-corroborated virtues is a legitimate, not a vanity,
    overturn. A candidate that only merely matches the incumbent ties and is
    deferred — recency alone never wins.
    """
    return CandidateOutput(
        strategy_id=f"standard:{standard.name}",
        output=standard.artifact,
        metadata={
            "virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0},
            "promotion_depth": standard.promotion_depth,
        },
    )


class StandardKeeper(InMemoryArbiter):
    """Critical loop over a ledger: promote D when ARETĒ rules it better.

    Extends :class:`InMemoryArbiter` so the standing standard is adjudicated by
    the same auditable non-compensatory rule — but the standard lives in the
    ledger (kind='standard'), wins strictly by merit, survives restarts, and is
    never overwritten by recency alone.
    """

    def __init__(
        self,
        store: MemoryStore,
        clock: Clock | None = None,
        weights: VirtueWeights | None = None,
        scorer: VirtueScorer | None = None,
        owner: Identity = DEFAULT_OWNER,
        standard_name: str = "truth",
    ) -> None:
        super().__init__(weights=weights, scorer=scorer)
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner
        self._standard_name = standard_name
        self._mnemosyne = Mnemosyne(store, self._clock)
        self._store = store

    # -- quiescent access --------------------------------------------------

    def current(self) -> Standard | None:
        """Return the standing standard from the ledger, or None if unset."""
        standards = self._store.find(kind="standard")
        if not standards:
            return None
        latest = standards[-1]
        payload = latest.get("payload", {})
        return Standard(
            name=str(payload.get("name", self._standard_name)),
            artifact=payload.get("artifact"),
            promotion_depth=int(payload.get("promotion_depth", 0)),
        )

    @property
    def store(self) -> MemoryStore:
        """The underlying ledger store (exposed for read/compose layers)."""
        return self._store

    def history(self) -> list[dict[str, Any]]:
        """The full, append-ordered promotion ledger (auditable trail)."""
        return list(self._store.find(kind="standard"))

    # -- the critical loop -------------------------------------------------

    def consider(self, proposal: CandidateOutput) -> PromotionResult:
        """Run a proposal against the standing standard; promote iff ARETĒ wins it.

        - No incumbent standard -> the proposal seeds the standard (uncontested
          first election, recorded).
        - Otherwise the proposal is pitted against the incumbent; only a
          hard-gate-passing, above-threshold, non-tied ALLOW for the proposal
          promotes it. DEFER -> deferred; DENY/older-wins -> rejected.
        """
        current = self.current()
        record_id: str | None = None

        if current is None:
            # Even the first standard must clear the justice hard-gate: it is
            # arbitrated against a refusal baseline, never self-seeded blindly.
            refusal = CandidateOutput(
                strategy_id="refusal",
                output="refuse",
                metadata={"virtues": {"justice": 1.0, "wisdom": 0.5, "courage": 1.0, "temperance": 1.0}},
            )
            first_dispute = Dispute(
                goal=f"Seed standard {proposal.strategy_id}",
                candidates=[proposal, refusal],
            )
            first_verdict = self.arbitrate(first_dispute)
            if (
                first_verdict.decision is not Verdict.ALLOW
                or first_verdict.winner_strategy_id != proposal.strategy_id
            ):
                return PromotionResult(
                    decision=PromotionDecision.REJECTED,
                    contender=proposal,
                    previous_standard=None,
                    current_standard=Standard(
                        name="refusal",
                        artifact="refuse",
                        promotion_depth=0,
                        evidence=_seed_bundle("rejected-first-election", proposal.strategy_id),
                    ),
                    verdict=first_verdict,
                )
            standard = Standard(
                name=proposal.strategy_id,
                artifact=proposal.output,
                promotion_depth=0,
                evidence=_seed_bundle("first-election", proposal.strategy_id),
            )
            record_id = self._record_standard(standard, {"election": "contested"})
            verdict = ArbitrationVerdict(
                decision=Verdict.ALLOW,
                winner_strategy_id=proposal.strategy_id,
                ranking=[proposal.strategy_id],
                scorecards=first_verdict.scorecards,
                reasoning=f"First synthesis seeded the standard '{proposal.strategy_id}' after clearing the justice gate.",
                evidence=first_verdict.evidence,
            )
            return PromotionResult(
                decision=PromotionDecision.PROMOTED,
                contender=proposal,
                previous_standard=None,
                current_standard=standard,
                verdict=verdict,
                record_id=record_id,
            )

        dispute = Dispute(
            goal=f"Promote {proposal.strategy_id} over {current.name}",
            candidates=[proposal, _as_candidate(current)],
        )
        verdict = self.arbitrate(dispute)

        if verdict.decision is Verdict.ALLOW and verdict.winner_strategy_id == proposal.strategy_id:
            standard = Standard(
                name=proposal.strategy_id,
                artifact=proposal.output,
                promotion_depth=current.promotion_depth + 1,
                evidence=verdict.evidence,
            )
            record_id = self._record_standard(standard, {"previous": current.name, "reasoning": verdict.reasoning})
            return PromotionResult(
                decision=PromotionDecision.PROMOTED,
                contender=proposal,
                previous_standard=current,
                current_standard=standard,
                verdict=verdict,
                record_id=record_id,
            )

        decision = (
            PromotionDecision.DEFERRED
            if verdict.decision is Verdict.DEFER
            else PromotionDecision.REJECTED
        )
        return PromotionResult(
            decision=decision,
            contender=proposal,
            previous_standard=current,
            current_standard=current,
            verdict=verdict,
        )

    # -- persistence -------------------------------------------------------

    def _record_standard(self, standard: Standard, meta: dict[str, object]) -> str:
        return self._mnemosyne.record(
            owner_id=self._owner.owner_id,
            kind="standard",
            payload={
                "name": standard.name,
                "artifact": standard.artifact,
                "promotion_depth": standard.promotion_depth,
                "evidence": _bundle_json(standard.evidence),
                "meta": meta,
            },
            provenance={"producer": "StandardKeeper", "owner_id": self._owner.owner_id},
        )


def _bundle_json(bundle: EvidenceBundle | None) -> list[dict[str, object]] | None:
    """Serialize an evidence bundle to plain ledger-friendly dicts."""
    if bundle is None:
        return None
    return [
        {
            "type": p.type_.value,
            "source": p.source.value,
            "value": p.value,
            "citation": p.citation,
            "weight": p.weight,
        }
        for p in bundle.points
    ]