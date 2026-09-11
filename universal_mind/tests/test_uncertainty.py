"""Tests for epistemic uncertainty — know what you do not know."""

from __future__ import annotations

from universal_mind.arete.uncertainty import (
    EpistemicStatus,
    assess_uncertainty,
)


def test_sufficient_evidence_is_known() -> None:
    result = assess_uncertainty(0.8)
    assert result.status is EpistemicStatus.KNOWN
    assert "sufficient" in result.reason


def test_thin_evidence_is_unknown() -> None:
    result = assess_uncertainty(0.2)
    assert result.status is EpistemicStatus.UNKNOWN
    assert "not enough to know" in result.reason


def test_conflict_overrides_even_strong_evidence() -> None:
    # Even with strong support, one genuine counter-evidence makes it conflicted.
    result = assess_uncertainty(0.9, conflicts=1)
    assert result.status is EpistemicStatus.CONFLICTED
    assert "counter-evidence" in result.reason


def test_threshold_is_configurable() -> None:
    result = assess_uncertainty(0.4, min_weight=0.3)
    assert result.status is EpistemicStatus.KNOWN
    result2 = assess_uncertainty(0.4, min_weight=0.5)
    assert result2.status is EpistemicStatus.UNKNOWN


def test_assessment_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    a = assess_uncertainty(0.8)
    try:
        a.status = EpistemicStatus.UNKNOWN  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_reason_is_never_empty() -> None:
    for w, c in [(0.8, 0), (0.1, 0), (0.9, 2)]:
        assert assess_uncertainty(w, conflicts=c).reason


def test_verdict_uncertainty_reads_evidence_weight() -> None:
    from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
    from universal_mind.arete.uncertainty import assess_verdict_uncertainty
    from universal_mind.powers.judgment import CandidateOutput

    dispute = Dispute(goal="pick", candidates=[
        CandidateOutput(strategy_id="x", output="out", metadata={
            "virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}})
    ])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = assess_verdict_uncertainty(verdict)
    # A clean ALLOW verdict carries measurable evidence -> KNOWN.
    assert result.status is EpistemicStatus.KNOWN
    assert result.evidence_weight > 0