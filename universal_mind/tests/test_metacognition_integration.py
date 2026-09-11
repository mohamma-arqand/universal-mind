"""Integration: metacognition folds the mind's real self-reasoning into one verdict."""

from __future__ import annotations

from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
from universal_mind.arete.counterfactual import counterfactual_check
from universal_mind.arete.uncertainty import assess_verdict_uncertainty
from universal_mind.core.metacognition import MetaConfidence, assess_metacognition
from universal_mind.demiurge.hypotheses import Hypothesis, HypothesisEnsemble
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id, output="out",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}},
    )


def test_metacognition_runs_over_a_real_verdict() -> None:
    """A strong, unambiguous decision should metacognitively score HIGH."""
    dispute = Dispute(goal="pick", candidates=[_candidate("good", 0.9), _candidate("bad", 0.2)])
    arbiter = InMemoryArbiter()
    verdict = arbiter.arbitrate(dispute)

    # Build the three self-reasoning products from the real verdict.
    cf = counterfactual_check(dispute, verdict, assumption="wisdom", arbiter=arbiter)
    # Ensemble over the two candidates as readings.
    ensemble = HypothesisEnsemble(margin=0.1).converge([
        Hypothesis("good", "reading", evidence_weight=0.9, simplicity=0.9),
        Hypothesis("bad", "reading", evidence_weight=0.2, simplicity=0.9),
    ])
    uncertainty = assess_verdict_uncertainty(verdict)

    meta = assess_metacognition(cf, uncertainty.status, ensemble)
    assert meta.confidence is MetaConfidence.MEDIUM or meta.confidence is MetaConfidence.HIGH
    assert "robust" in meta.axes


def test_weak_decision_scores_skeptical() -> None:
    """A thin, fragile decision should metacognitively score SKEPTICAL or LOW."""
    dispute = Dispute(goal="pick", candidates=[_candidate("only", 0.5), _candidate("tie", 0.5)])
    arbiter = InMemoryArbiter()
    verdict = arbiter.arbitrate(dispute)

    cf = counterfactual_check(dispute, verdict, assumption="wisdom", arbiter=arbiter)
    ensemble = HypothesisEnsemble(margin=0.1).converge([
        Hypothesis("only", "r", 0.5, 0.5), Hypothesis("tie", "r", 0.5, 0.5),
    ])
    uncertainty = assess_verdict_uncertainty(verdict)

    meta = assess_metacognition(cf, uncertainty.status, ensemble)
    # A tied/fragile decision must not be trusted highly.
    assert meta.confidence in (MetaConfidence.LOW, MetaConfidence.SKEPTICAL)