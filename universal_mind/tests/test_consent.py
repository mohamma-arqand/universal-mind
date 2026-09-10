"""Tests for human-in-the-loop consent over ARETĒ promotions."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.feedback import (
    HumanVerdict,
    PromotionConsent,
)
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}


def _candidate(name: str, virtues: dict[str, float] | None = None) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=name,
        output="artifact",
        metadata={"virtues": virtues or dict(FULL)},
    )


def _keeper() -> StandardKeeper:
    return StandardKeeper(InMemoryStore())


def test_default_consent_keeps_promotion_tentative() -> None:
    """Deny-by-default: without explicit human consent, nothing finalizes."""
    keeper = _keeper()
    consent = PromotionConsent(keeper)
    out = consent.consider(_candidate("D1"))
    assert out.human_verdict is HumanVerdict.VETO
    assert out.finalized is False


def test_explicit_consent_finalizes() -> None:
    keeper = _keeper()
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.CONSENT)
    out = consent.consider(_candidate("D1"))
    assert out.human_verdict is HumanVerdict.CONSENT
    assert out.finalized is True


def test_consent_recorded_in_ledger() -> None:
    """A human ruling is committed as a first-class ledger record."""
    keeper = _keeper()
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.VETO)
    consent.consider(_candidate("D1"))
    kinds = [r.get("kind") for r in keeper.store.read_all()]
    assert "human_consent" in kinds
    consent_rec = [r for r in keeper.store.read_all() if r.get("kind") == "human_consent"]
    assert consent_rec
    assert consent_rec[-1]["payload"]["contender"] == "D1"


def test_consent_evidence_is_human_source() -> None:
    keeper = _keeper()
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.CONSENT)
    out = consent.consider(_candidate("D1"))
    assert out.evidence.has_human()
    assert out.evidence.strongest().value == "consent"


def test_veto_never_finalizes_even_if_arete_promotes() -> None:
    """A veto blocks finalization regardless of the underlying verdict."""
    keeper = _keeper()
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.VETO)
    out = consent.consider(_candidate("D1"))
    assert out.finalized is False
    assert out.human_verdict is HumanVerdict.VETO


def test_arete_still_arbitrates_first() -> None:
    """The keeper's non-compensatory arbitration still runs before consent."""
    keeper = _keeper()
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.CONSENT)
    # A justice-failing candidate is rejected by ARETĒ, so it never finalizes.
    out = consent.consider(_candidate("unjust", {"justice": 0.1, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}))
    assert out.finalized is False
    assert out.promotion_decision.value == "rejected"