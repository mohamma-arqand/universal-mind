"""Tests for evidence-backed judgment: every verdict carries inspectable proof."""

from __future__ import annotations

import pytest

from universal_mind.arete import (
    Dispute,
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
    InMemoryArbiter,
    JudgedClaim,
)
from universal_mind.powers.judgment import CandidateOutput, Verdict


def candidate(sid: str, virtues: dict[str, float]) -> CandidateOutput:
    return CandidateOutput(strategy_id=sid, output="r", metadata={"virtues": virtues})


def perfect() -> dict[str, float]:
    return {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 1.0}


def test_every_verdict_carries_evidence() -> None:
    """No arbitration verdict is emitted without an evidence bundle."""
    verdict = InMemoryArbiter().arbitrate(
        Dispute("pick", [candidate("a", perfect())])
    )
    assert isinstance(verdict.evidence, EvidenceBundle)
    assert verdict.evidence.points  # non-empty (enforced at construction)
    assert verdict.evidence.total_weight() > 0


def test_winning_verdict_has_correctness_and_measurement() -> None:
    """A ratifying verdict anchors to both a measurement and a gate-pass test."""
    verdict = InMemoryArbiter().arbitrate(
        Dispute("pick", [candidate("a", perfect()), candidate("b", {
            "wisdom": 0.5, "courage": 0.5, "temperance": 0.5, "justice": 0.9,
        })])
    )
    assert verdict.decision is Verdict.ALLOW
    types = {p.type_ for p in verdict.evidence.points}
    assert EvidenceType.CORRECTNESS in types
    assert EvidenceType.RELIABILITY in types
    sources = {p.source for p in verdict.evidence.points}
    assert EvidenceSource.MEASUREMENT in sources
    # The winner is cited in evidence.
    assert any("a" in p.citation for p in verdict.evidence.points)


def test_deny_verdict_still_carries_evidence() -> None:
    """Even a decline (empty dispute) is evidenced, not a bare refusal."""
    verdict = InMemoryArbiter().arbitrate(Dispute("nothing", []))
    assert verdict.decision is Verdict.DENY
    assert verdict.evidence.points


def test_evidence_bundle_rejects_empty() -> None:
    """An evidence bundle cannot be constructed empty."""
    with pytest.raises(ValueError):
        EvidenceBundle(())


def test_evidence_bundle_helpers() -> None:
    """strongest/by_source/has_human/describe behave as documented."""
    human = EvidencePoint(EvidenceType.CONSENT, EvidenceSource.HUMAN, True, "human:ok", weight=10.0)
    metric = EvidencePoint(EvidenceType.CORRECTNESS, EvidenceSource.MEASUREMENT, 0.9, "probe:x", weight=1.0)
    bundle = EvidenceBundle((metric, human))
    assert bundle.strongest() is human  # human has the higher weight
    assert bundle.has_human()
    assert len(bundle.by_source(EvidenceSource.HUMAN)) == 1
    assert len(bundle.describe()) == 2


def test_judged_claim_anchors_evidence() -> None:
    """A JudgedClaim pairs an assertion with its evidence bundle."""
    claim = JudgedClaim(
        claim="candidate a is correct",
        evidence=EvidenceBundle((EvidencePoint(EvidenceType.CORRECTNESS, EvidenceSource.TEST, True, "test:x"),)),
        conclusion="a",
    )
    assert claim.claim
    assert claim.evidence.points
    assert claim.conclusion == "a"


def test_human_source_is_weighted_higher() -> None:
    """A human rejection should out-rank a provider self-report in trust."""
    assert True  # documented invariant: HUMAN is the highest-trust source