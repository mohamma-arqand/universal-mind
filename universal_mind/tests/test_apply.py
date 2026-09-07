"""Tests for the evolution application layer (reversible, policy-gated)."""

from __future__ import annotations

from typing import Any

import pytest

from universal_mind.core.clock import SystemClock
from universal_mind.core.executive import ExecutionThrottle, ExecutiveMind
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.registry import PantheonRegistry
from universal_mind.prometheus import (
    FallbackOrderApplier,
    ThrottleApplier,
    apply_proposal,
    evolve_and_apply,
)
from universal_mind.prometheus.proposer import EvolutionProposal, ProposalKind, Risk


def _append(store: InMemoryStore, kind: str, payload: dict[str, Any]) -> None:
    store.append(
        {
            "owner_id": "sovereign",
            "kind": kind,
            "created_at": "2026-09-07T00:00:00+00:00",
            "payload": payload,
            "provenance": {"producer": "test"},
        }
    )


def _mk_executive(throttle: ExecutionThrottle | None = None) -> ExecutiveMind:
    store = InMemoryStore()
    return ExecutiveMind(
        registry=PantheonRegistry(store),
        memory=Mnemosyne(store, SystemClock()),
        clock=SystemClock(),
        throttle=throttle if throttle is not None else ExecutionThrottle(),
    )


def _throttle_store() -> InMemoryStore:
    """3 successful runs + 3 faults -> high error rate -> TIGHTEN_THROTTLE."""
    store = InMemoryStore()
    for _ in range(3):
        _append(store, "capability_result", {"ok": True, "output": "x", "cost": 1.0, "notes": []})
        _append(store, "fault", {"fault_class": "task_failure"})
    return store


def _fallback_store() -> InMemoryStore:
    """3 failed results on 'flaky' -> REORDER_FALLBACK (+ REVIEW)."""
    store = InMemoryStore()
    for _ in range(3):
        _append(store, "capability_selected", {"name": "flaky"})
        _append(store, "capability_result", {"ok": False, "output": "x", "cost": 1.0, "notes": []})
    return store


def _proposal(kind: ProposalKind) -> EvolutionProposal:
    return EvolutionProposal(
        kind=kind,
        target="x",
        reason="test",
        risk=Risk.LOW,
        reversible=True,
        suggested_change="s",
        evidence={"executions": 5},
    )


def test_throttle_proposal_reused_from_engine() -> None:
    """ThrottleApplier (engine) realizes a TIGHTEN_THROTTLE proposal reversibly."""
    throttle = ExecutionThrottle(error_rate_threshold=0.2)
    applier = ThrottleApplier(throttle, step=0.05, min_threshold=0.01)
    proposal = _proposal(ProposalKind.TIGHTEN_THROTTLE)
    outcome = applier.apply(proposal)
    assert "applied" in outcome and "0.200" in outcome and "0.150" in outcome
    assert throttle.error_rate_threshold == pytest.approx(0.15)
    applier.undo(proposal)
    assert throttle.error_rate_threshold == pytest.approx(0.2)


def test_throttle_applier_floor() -> None:
    """ThrottleApplier never lowers below its configured floor."""
    throttle = ExecutionThrottle(error_rate_threshold=0.02)
    applier = ThrottleApplier(throttle, step=0.05, min_threshold=0.01)
    applier.apply(_proposal(ProposalKind.TIGHTEN_THROTTLE))
    assert throttle.error_rate_threshold == 0.01


def test_fallback_applier_installs_and_undo() -> None:
    """FallbackOrderApplier installs a fallback chain and restores it on undo."""
    executive = _mk_executive()
    applier = FallbackOrderApplier(executive.error_handler, fallback="echo")
    proposal = _proposal(ProposalKind.REORDER_FALLBACK)
    outcome = applier.apply(proposal)
    assert "installed fallback chain" in outcome
    assert executive.error_handler.fallback_capability == ["echo"]
    applier.undo(proposal)
    assert executive.error_handler.fallback_capability is None


def test_fallback_applier_ignores_other_kinds() -> None:
    """FallbackOrderApplier ignores proposals it does not own."""
    executive = _mk_executive()
    applier = FallbackOrderApplier(executive.error_handler)
    outcome = applier.apply(_proposal(ProposalKind.CHAMPION))
    assert "ignored" in outcome
    assert executive.error_handler.fallback_capability is None


def test_apply_proposal_routes_unsupported_kind() -> None:
    """apply_proposal routes to the right applier and ignores the rest."""
    executive = _mk_executive()
    throttle = ThrottleApplier(executive.throttle)
    fallback = FallbackOrderApplier(executive.error_handler)
    outcome = apply_proposal(_proposal(ProposalKind.RESPECT_VETO), throttle, fallback)
    assert "ignored" in outcome.detail


def test_evolve_and_apply_tightens_executive() -> None:
    """The composed loop realizes a throttle proposal on the live executive."""
    executive = _mk_executive(throttle=ExecutionThrottle(error_rate_threshold=0.5))
    store = _throttle_store()
    _, outcomes = evolve_and_apply(store, executive)
    assert any(o.kind == ProposalKind.TIGHTEN_THROTTLE for o in outcomes)
    # Default ThrottleApplier step 0.05 lowered it.
    assert executive.throttle.error_rate_threshold < 0.5


def test_evolve_and_apply_installs_fallback() -> None:
    """The composed loop realizes a fallback proposal on the executive."""
    executive = _mk_executive()
    store = _fallback_store()
    _, outcomes = evolve_and_apply(store, executive)
    assert any(o.kind == ProposalKind.REORDER_FALLBACK for o in outcomes)
    assert executive.error_handler.fallback_capability == ["echo"]


def test_evolve_and_apply_returns_report_and_all_outcomes() -> None:
    """One outcome per proposal, and the evolution report is intact."""
    executive = _mk_executive()
    report, outcomes = evolve_and_apply(_fallback_store(), executive)
    assert len(outcomes) == report.proposal_count
    assert report.proposals


def test_evolve_and_apply_deterministic() -> None:
    """Identical inputs and stores yield identical outcomes/threshold."""
    def run() -> float:
        exec_h = _mk_executive(throttle=ExecutionThrottle(error_rate_threshold=0.5))
        _, outs = evolve_and_apply(_throttle_store(), exec_h)
        assert outs
        return exec_h.throttle.error_rate_threshold

    assert run() == run()