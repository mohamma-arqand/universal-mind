"""Tests for metacognition — the mind reasons about its own reasoning."""

from __future__ import annotations

from universal_mind.arete.counterfactual import CounterfactualResult
from universal_mind.arete.uncertainty import EpistemicStatus
from universal_mind.core.metacognition import (
    MetaConfidence,
    assess_metacognition,
)
from universal_mind.demiurge.hypotheses import EnsembleResult, Hypothesis


def _robust(robust: bool) -> CounterfactualResult:
    return CounterfactualResult(
        original_winner="x", robust=robust, counterfactual_winner="x",
        explanation="e", reversed_dimension="wisdom", original_value=0.9, reversed_value=0.1,
    )


def _ensemble(converged: bool) -> EnsembleResult:
    h = Hypothesis(hypothesis_id="a", reading="r", evidence_weight=0.9, simplicity=0.9)
    return EnsembleResult(ranked=(h,), best=h, alternatives=(), converged=converged)


def test_all_axes_pass_is_high() -> None:
    v = assess_metacognition(_robust(True), EpistemicStatus.KNOWN, _ensemble(True))
    assert v.confidence is MetaConfidence.HIGH
    assert v.axes == {"robust": True, "known": True, "converged": True}


def test_two_axes_is_medium() -> None:
    v = assess_metacognition(_robust(True), EpistemicStatus.KNOWN, _ensemble(False))
    assert v.confidence is MetaConfidence.MEDIUM


def test_only_robust_is_low() -> None:
    v = assess_metacognition(_robust(True), EpistemicStatus.UNKNOWN, _ensemble(False))
    assert v.confidence is MetaConfidence.LOW


def test_only_known_is_skeptical() -> None:
    # A decision that is "known" but neither robust nor converged is not trusted.
    v = assess_metacognition(_robust(False), EpistemicStatus.KNOWN, _ensemble(False))
    assert v.confidence is MetaConfidence.SKEPTICAL


def test_no_inputs_is_skeptical() -> None:
    v = assess_metacognition()
    assert v.confidence is MetaConfidence.SKEPTICAL
    assert all(not ok for ok in v.axes.values())


def test_verdict_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    v = assess_metacognition()
    try:
        v.confidence = MetaConfidence.HIGH  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True