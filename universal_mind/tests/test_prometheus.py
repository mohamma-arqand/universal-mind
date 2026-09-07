"""Tests for PROMETHEUS: metrics, proposals, policy vetting, and gated apply."""

from __future__ import annotations

from typing import Any

from universal_mind.memory.store import InMemoryStore
from universal_mind.prometheus import (
    EvolutionPolicy,
    EvolutionProposal,
    InMemoryApplier,
    InMemoryPrometheus,
    NoopApplier,
    Prometheus,
    ProposalKind,
    Risk,
    compute_metrics,
)
from universal_mind.prometheus.proposer import PrometheusProposer


def _append(store: InMemoryStore, kind: str, payload: dict[str, Any], **extra: Any) -> str:
    """Append a minimal ledger record to the store."""
    return store.append(
        {
            "owner_id": "sovereign",
            "kind": kind,
            "created_at": "2026-09-07T00:00:00+00:00",
            "payload": payload,
            "provenance": {"producer": "test"},
            **extra,
        }
    )


def _run(name: str, ok: bool, store: InMemoryStore) -> None:
    """Select ``name`` then run one result against it."""
    _append(store, "capability_selected", {"name": name})
    _append(store, "capability_result", {"ok": ok, "output": "x", "cost": 1.0, "notes": []})


def _history(flaky_runs: int = 3, flaky_ok: bool = False) -> InMemoryStore:
    """A store where 'flaky' mostly fails; used for low-success scenarios."""
    store = InMemoryStore()
    for _ in range(flaky_runs):
        _run("flaky", flaky_ok, store)
    return store


def test_compute_metrics_empty() -> None:
    """An empty ledger yields a zeroed snapshot."""
    metrics = compute_metrics([])
    assert metrics.executions == 0
    assert metrics.faults == 0
    assert metrics.error_rate == 0.0
    assert metrics.capabilities == ()


def test_compute_metrics_counts_success_and_faults() -> None:
    """Successes, faults, and error-rate are derived correctly."""
    store = InMemoryStore()
    _run("a", True, store)
    _run("a", True, store)
    _append(store, "fault", {"fault_class": "task_failure"})
    _append(store, "fault", {"fault_class": "task_failure"})
    metrics = compute_metrics(list(store.read_all()))
    assert (metrics.executions, metrics.successes, metrics.faults) == (2, 2, 2)
    assert metrics.error_rate == 1.0
    assert metrics.fault_classes == {"task_failure": 2}


def test_compute_metrics_attributes_to_selected_capability() -> None:
    """Results are attributed to the most recently selected capability."""
    store = InMemoryStore()
    _run("echo", True, store)
    _run("echo", False, store)
    metrics = compute_metrics(list(store.read_all()))
    echo = next(c for c in metrics.capabilities if c.name == "echo")
    assert (echo.executions, echo.successes) == (2, 1)
    assert echo.success_rate == 0.5


def test_compute_metrics_feedback() -> None:
    """Feedback verdicts are counted across three buckets."""
    store = InMemoryStore()
    for verdict in ("approved", "rejected", "rejected", "needs_work"):
        _append(store, "feedback", {"verdict": verdict, "target_record_id": "t1"})
    metrics = compute_metrics(list(store.read_all()))
    assert (metrics.feedback_approved, metrics.feedback_rejected, metrics.feedback_needs_work) == (1, 2, 1)


def test_proposer_sparse_field_produces_nothing() -> None:
    """Too few observations produce no proposals (avoid acting on noise)."""
    proposer = PrometheusProposer()
    metrics = compute_metrics(list(_history(flaky_runs=1, flaky_ok=False).read_all()))
    assert proposer.compose(metrics) == []


def test_proposer_flags_low_success_capability() -> None:
    """A failing capability is surfaced for review with evidence."""
    proposer = PrometheusProposer()
    metrics = compute_metrics(list(_history(flaky_runs=3, flaky_ok=False).read_all()))
    proposals = proposer.compose(metrics)
    kinds = [p.kind for p in proposals]
    assert ProposalKind.REVIEW_CAPABILITY in kinds
    review = next(p for p in proposals if p.kind == ProposalKind.REVIEW_CAPABILITY)
    assert review.target == "flaky"
    assert review.risk is Risk.MEDIUM
    assert review.evidence.get("executions") == 3


def test_proposer_tighten_on_high_error_rate() -> None:
    """A high overall error rate yields a throttle-tuning proposal."""
    store = InMemoryStore()
    for _ in range(3):
        _run("a", True, store)
        _append(store, "fault", {"fault_class": "system_fault"})
    metrics = compute_metrics(list(store.read_all()))
    proposals = PrometheusProposer().compose(metrics)
    assert any(p.kind == ProposalKind.TIGHTEN_THROTTLE for p in proposals)


def test_proposer_respects_human_veto() -> None:
    """Repeated human rejection surfaces a respect-veto proposal."""
    store = _history(flaky_runs=3, flaky_ok=True)
    for _ in range(2):
        _append(store, "feedback", {"verdict": "rejected", "target_record_id": "t1"})
    metrics = compute_metrics(list(store.read_all()))
    proposals = PrometheusProposer().compose(metrics)
    assert any(p.kind == ProposalKind.RESPECT_VETO for p in proposals)


def test_policy_rejects_high_risk_and_irreversible() -> None:
    """The default policy blocks HIGH-risk and irreversible proposals."""
    policy = EvolutionPolicy()
    high = EvolutionProposal(
        kind=ProposalKind.REORDER_FALLBACK, target="x", reason="r",
        risk=Risk.HIGH, reversible=True, suggested_change="s", evidence={"executions": 5},
    )
    irreversible = EvolutionProposal(
        kind=ProposalKind.REVIEW_CAPABILITY, target="x", reason="r",
        risk=Risk.LOW, reversible=False, suggested_change="s", evidence={"executions": 5},
    )
    assert not policy.allows(high)
    assert not policy.allows(irreversible)
    assert policy.reject_reason(high) is not None
    assert policy.reject_reason(irreversible) is not None


def test_policy_vet_partitions() -> None:
    """vet() splits proposals into (allowed, [(rejected, reason)])."""
    allowed = EvolutionProposal(
        kind=ProposalKind.CHAMPION, target="x", reason="r",
        risk=Risk.LOW, reversible=True, suggested_change="s", evidence={"executions": 5},
    )
    denied = EvolutionProposal(
        kind=ProposalKind.REVIEW_CAPABILITY, target="y", reason="r",
        risk=Risk.HIGH, reversible=True, suggested_change="s", evidence={"executions": 5},
    )
    ok, rejected = EvolutionPolicy().vet([allowed, denied])
    assert [p.target for p in ok] == ["x"]
    assert len(rejected) == 1 and rejected[0][0].target == "y"


def test_noop_applier_is_proposals_only() -> None:
    """The default applier changes nothing and reports 'proposals-only'."""
    store = _history(flaky_runs=3, flaky_ok=False)
    report = InMemoryPrometheus(store, applier=NoopApplier()).evolve()
    assert any(p.kind == ProposalKind.REVIEW_CAPABILITY for p in report.proposals)
    # Vetted proposals were 'applied' only as a manual-ratify note.
    assert report.applied
    assert all("proposals-only" in outcome for _, outcome in report.applied)
    # The ledger is untouched.
    assert len(list(store.read_all())) == 6


def test_inmemory_applier_applies_and_undoes() -> None:
    """With an explicit reversible applier, apply writes to an in-memory config."""
    store = _history(flaky_runs=3, flaky_ok=False)
    applier = InMemoryApplier()
    report = InMemoryPrometheus(store, applier=applier).evolve()
    assert any(p.kind == ProposalKind.REVIEW_CAPABILITY for p in report.proposals)
    assert applier.config.get("evolve:review_capability") is not None
    # Undo restores the config to its prior (empty) state.
    for kind in list(applier.config):
        proposal = next(p for p in report.proposals if p.kind.value == kind.split(":", 1)[1])
        applier.undo(proposal)
    assert applier.config == {}


def test_inmemory_prometheus_is_deterministic() -> None:
    """Identical ledger state yields an identical report."""
    def run_once() -> str:
        store = _history(flaky_runs=3, flaky_ok=False)
        report = InMemoryPrometheus(store).evolve()
        return "|".join(sorted(p.kind.value for p in report.proposals))

    assert run_once() == run_once()


def test_prometheus_protocol_conformance() -> None:
    """InMemoryPrometheus conforms to the Prometheus protocol."""
    engine: Prometheus = InMemoryPrometheus(_history(flaky_runs=3))
    assert isinstance(engine, Prometheus)


def test_report_summary_shape() -> None:
    """The report carries the auditable summary counts."""
    store = _history(flaky_runs=3, flaky_ok=False)
    report = InMemoryPrometheus(store).evolve()
    assert report.proposal_count == len(report.proposals)
    assert report.applied_count == len(report.applied)
    assert report.proposals
    assert "proposal" in report.summary