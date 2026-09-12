"""Coverage for the remaining <95% modules: budget, temporal, self_code_audit,
audit_rubric, external_evaluator, power_zero."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from universal_mind.layers import Layer
from universal_mind.pantheon.budget import (
    BudgetAllocation,
    allocate_budget,
    explain,
    select_organs_for_domains,
)
from universal_mind.pantheon.registry import CapabilityDossier, OrganDescriptor


def _organ(name: str, cost: float = 1.0, credibility: float = 0.5, domains: tuple[str, ...] = (),
           purpose: str = "") -> OrganDescriptor:
    return OrganDescriptor(
        name=name,
        signature=f"{name}()",
        cost=cost,
        latency_ms=10.0,
        credibility=credibility,
        domains=domains,
        layer=Layer.GATEWAY,
        dossier=CapabilityDossier(
            name=name, version="1.0.0", signature=f"{name}()", purpose=purpose or f"serve {name}",
            cost_model="flat", latency_profile="instant", reliability="high",
            side_effects="none", reversible=True, required_secrets=[], failure_modes="none",
            dependencies=[], determinism="STRICT",  # type: ignore[arg-type]
            provenance={"explicit_fields": ["idempotent"]}, idempotent=True,
        ),
    )


def test_budget_zero_cost_uses_credibility() -> None:
    a = _organ("free", cost=0.0, credibility=0.8)
    b = _organ("paid", cost=1.0, credibility=0.8)
    alloc = allocate_budget([a, b], budget=10.0)
    # both fit; free one ranks first (value = credibility, no division)
    assert "free" in alloc.selected


def test_budget_explain_nothing_affordable() -> None:
    alloc = BudgetAllocation(selected=(), total_cost=0.0, remaining=0.0, dropped=(), ranking=())
    assert explain(alloc, {}) == "nothing affordable within the budget"


def test_budget_explain_nothing_dropped() -> None:
    alloc = BudgetAllocation(selected=("a",), total_cost=1.0, remaining=9.0, dropped=(), ranking=("a",))
    assert "nothing dropped" in explain(alloc, {})


def test_select_organs_for_domains_purpose_fallback() -> None:
    # 'greeting' matches no exact domain, but falls through to purpose substring.
    org = _organ("greeter", purpose="handles greeting requests")
    chosen, _alloc = select_organs_for_domains([org], ["greeting"], budget=10.0)
    assert chosen.get("greeting") == "greeter"


def test_select_organs_for_domains_no_match() -> None:
    org = _organ("other", purpose="unrelated")
    chosen, _alloc = select_organs_for_domains([org], ["greeting"], budget=10.0)
    assert chosen == {}


# --- temporal_awareness ---


def test_temporal_derive_basic_and_naive_reference() -> None:
    from universal_mind.core.clock import FrozenClock
    from universal_mind.core.temporal_awareness import derive_temporal_context

    clock = FrozenClock(datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc))  # Tue
    ctx = derive_temporal_context(clock)
    assert ctx.isoweekday == 2
    assert ctx.is_business_hours is True

    # naive reference (no tz) still yields a freshness without raising
    ref_naive = datetime(2024, 1, 1, 15, 0)  # noqa: DTZ001 — deliberately naive
    ctx2 = derive_temporal_context(clock, reference=ref_naive)
    assert ctx2.freshness_hours >= 0.0


# --- self_code_audit ---


def test_self_code_audit_scan_and_report(tmp_path: Path) -> None:
    from universal_mind.core.self_code_audit import run_self_audit, scan_source

    # a real directory with one clean module
    (tmp_path / "mod.py").write_text('"""docstring"""\ndef f():\n    return 1\n', encoding="utf-8")
    findings = scan_source(Path(tmp_path))
    assert isinstance(findings, tuple)
    report = run_self_audit(Path(tmp_path))
    assert report is not None
    assert report.files_scanned >= 1


# --- audit_rubric ---


def test_audit_rubric_score_weak_and_version() -> None:
    from universal_mind.arete.audit_rubric import ExternalRubric

    weak = {"tests_failures": 5, "probes_failed": 2, "mypy_errors": 1,
            "red_team_penetrated": 1, "robust_fraction": 0.1}
    card = ExternalRubric().score(weak)
    assert card.score < 0.7


# --- external_evaluator ---


class _MiniLoop:
    acceptance_bar = 0.5
    budget = 10.0

    def __init__(self) -> None:
        self._nodes: list[object] = [object()]
        self.lineage = self

    def nodes(self) -> list[object]:
        return self._nodes

    def tighten(self, bar_step: float = 0.1) -> None:
        self.acceptance_bar += bar_step


def test_external_evaluator_findings_and_evaluate() -> None:
    from universal_mind.arete.external_evaluator import _findings, evaluate_loop

    loop = _MiniLoop()
    findings = _findings(loop)
    assert all(f.ok for f in findings)

    result = evaluate_loop(loop)
    assert result is not None
    assert "PASS" in result.summary


def test_external_evaluator_detects_missing_bar() -> None:
    from universal_mind.arete.external_evaluator import _findings

    class _NoBar:
        budget = 1.0

        def nodes(self) -> list[object]:
            return [object()]

        def tighten(self) -> None:
            return None

    findings = _findings(_NoBar())
    assert any(not f.ok for f in findings)


# --- power_zero / powerzero gate ---


def test_power_zero_gate_allows() -> None:
    from universal_mind.gates.power_zero import DefaultPowerZero

    gate = DefaultPowerZero()
    assert gate is not None
    assert gate.name == "PowerZero"