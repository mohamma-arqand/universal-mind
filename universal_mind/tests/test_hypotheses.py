"""Tests for the hypothesis ensemble — several readings, converge on evidence."""

from __future__ import annotations

from universal_mind.demiurge.hypotheses import (
    EnsembleResult,
    Hypothesis,
    HypothesisEnsemble,
    score_hypothesis,
)


def _h(hypothesis_id: str, evidence: float, simplicity: float) -> Hypothesis:
    return Hypothesis(hypothesis_id=hypothesis_id, reading=hypothesis_id, evidence_weight=evidence, simplicity=simplicity)


def test_best_reading_is_ranked_first() -> None:
    ensemble = HypothesisEnsemble()
    result = ensemble.converge([_h("weak", 0.2, 0.9), _h("strong", 0.9, 0.9)])
    assert result.best is not None
    assert result.best.hypothesis_id == "strong"
    assert result.ranked[0].hypothesis_id == "strong"


def test_alternatives_stay_live() -> None:
    ensemble = HypothesisEnsemble(min_alternatives=2)
    result = ensemble.converge([_h("a", 0.9, 0.9), _h("b", 0.6, 0.9), _h("c", 0.5, 0.9)])
    assert result.best is not None
    assert result.best.hypothesis_id == "a"
    assert {h.hypothesis_id for h in result.alternatives} == {"b", "c"}


def test_converged_when_margin_is_decisive() -> None:
    ensemble = HypothesisEnsemble(margin=0.1)
    result = ensemble.converge([_h("a", 0.9, 0.9), _h("b", 0.3, 0.9)])
    assert result.converged is True


def test_not_converged_when_margin_is_thin() -> None:
    ensemble = HypothesisEnsemble(margin=0.1)
    result = ensemble.converge([_h("a", 0.6, 0.5), _h("b", 0.55, 0.5)])
    assert result.converged is False
    assert result.best is not None
    assert result.best.hypothesis_id == "a"  # still reports best, but not decisive


def test_empty_ensemble_is_not_converged() -> None:
    result = HypothesisEnsemble().converge([])
    assert result.best is None
    assert result.converged is False
    assert result.alternatives == ()


def test_score_prefers_evidence_over_simplicity() -> None:
    # More evidence, less simplicity beats less evidence, more simplicity.
    assert score_hypothesis(_h("x", 0.9, 0.1)) > score_hypothesis(_h("y", 0.2, 1.0))


def test_result_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    result = EnsembleResult((), None, (), False)
    try:
        result.converged = True  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True