"""Tests for the self-awareness ⇄ Prometheus bridge (SELF_CORRECT proposal)."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.prometheus.apply import SelfCorrectApplier
from universal_mind.prometheus.metrics import compute_metrics
from universal_mind.prometheus.proposer import (
    EvolutionProposal,
    PrometheusProposer,
    ProposalKind,
    Risk,
)


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def _proposal() -> EvolutionProposal:
    return EvolutionProposal(
        kind=ProposalKind.SELF_CORRECT,
        target="executive.self_awareness",
        reason="judgment unhealthy",
        risk=Risk.LOW,
        reversible=True,
        suggested_change="raise bar / cut budget",
        evidence={"judgment_unhealthy": True},
    )


def test_self_correct_applier_tightens_bar_and_budget() -> None:
    loop = _loop()
    applier = SelfCorrectApplier(loop)
    result = applier.apply(_proposal())
    assert "tightened" in result
    assert loop.acceptance_bar > 0.9
    assert loop.budget < 100.0


def test_self_correct_applier_undo_restores() -> None:
    loop = _loop()
    applier = SelfCorrectApplier(loop)
    applier.apply(_proposal())
    bar_after = loop.acceptance_bar
    applier.undo(_proposal())
    assert loop.acceptance_bar == 0.9
    assert loop.budget == 100.0
    assert bar_after > 0.9  # sanity: it really did tighten first


def test_self_correct_applier_ignores_other_kinds() -> None:
    loop = _loop()
    applier = SelfCorrectApplier(loop)
    other = EvolutionProposal(
        kind=ProposalKind.CHAMPION,
        target="x",
        reason="r",
        risk=Risk.LOW,
        reversible=True,
        suggested_change="s",
        evidence={},
    )
    result = applier.apply(other)
    assert "ignored" in result
    assert loop.acceptance_bar == 0.9


def test_metrics_derives_judgment_unhealthy_from_ledger() -> None:
    healthy_records = [
        {"kind": "self_awareness", "payload": {"action_taken": False}},
    ]
    metrics = compute_metrics(healthy_records)
    assert metrics.judgment_unhealthy is False

    unhealthy_records = [
        {"kind": "self_awareness", "payload": {"action_taken": False}},
        {"kind": "self_awareness", "payload": {"action_taken": True}},
    ]
    metrics2 = compute_metrics(unhealthy_records)
    assert metrics2.judgment_unhealthy is True


def test_proposer_emits_self_correct_when_unhealthy() -> None:
    from universal_mind.prometheus.metrics import EvolutionMetrics

    metrics = EvolutionMetrics(executions=5, judgment_unhealthy=True)
    proposals = PrometheusProposer().compose(metrics)
    kinds = [p.kind for p in proposals]
    assert ProposalKind.SELF_CORRECT in kinds


def test_proposer_silent_when_healthy() -> None:
    from universal_mind.prometheus.metrics import EvolutionMetrics

    metrics = EvolutionMetrics(executions=5, judgment_unhealthy=False)
    proposals = PrometheusProposer().compose(metrics)
    kinds = [p.kind for p in proposals]
    assert ProposalKind.SELF_CORRECT not in kinds