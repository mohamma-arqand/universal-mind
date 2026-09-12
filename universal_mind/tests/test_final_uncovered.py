"""Coverage for the final <95% modules: power_zero gate, apply, audit_rubric,
self_code_audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from universal_mind.core.intent import Determinism, Intent
from universal_mind.gates.base import Verdict as GateVerdict
from universal_mind.gates.power_zero import (
    AlwaysVetoPowerZero,
    ConditionalVetoPowerZero,
    DefaultPowerZero,
    PowerZero,
)
from universal_mind.prometheus.apply import (
    FallbackOrderApplier,
    SelfCorrectApplier,
    apply_proposal,
)
from universal_mind.prometheus.proposer import EvolutionProposal, ProposalKind, Risk


def _intent(goal: str = "x") -> Intent:
    return Intent(raw_text=goal, goal=goal, success_criteria=["ok"], constraints=[],
                  deadline=None, determinism=Determinism.STRICT, owner_id="o")


def _prop(kind: ProposalKind) -> EvolutionProposal:
    return EvolutionProposal(
        kind=kind, target="t", reason="r", risk=Risk.LOW, reversible=True,
        suggested_change="x", evidence={"executions": 10},
    )


# --- gates/power_zero ---


def test_power_zero_precedence_and_raise_without_intent() -> None:
    gate = PowerZero()
    assert gate.precedence == 1000
    with pytest.raises(ValueError):
        gate.evaluate({})


def test_power_zero_veto_variants() -> None:
    assert DefaultPowerZero().evaluate({"intent": _intent()}) == GateVerdict.ALLOW
    assert AlwaysVetoPowerZero().evaluate({"intent": _intent()}) == GateVerdict.DENY

    cond = ConditionalVetoPowerZero(veto_goals=["forbidden"])
    assert cond.evaluate({"intent": _intent("forbidden")}) == GateVerdict.DENY
    assert cond.evaluate({"intent": _intent("ok")}) == GateVerdict.ALLOW


# --- prometheus/apply ---


class _FakeLoop:
    def __init__(self) -> None:
        self.acceptance_bar = 0.5
        self.budget = 10.0
        self._bar = 0.5
        self._budget = 10.0

    def tighten(self) -> tuple[float, float]:
        self._bar = min(1.0, self._bar + 0.1)
        self._budget = max(0.0, self._budget - 1.0)
        return self._bar, self._budget


def test_fallback_undo_nothing() -> None:
    from universal_mind.core.errors import ErrorHandler

    handler = ErrorHandler()
    applier = FallbackOrderApplier(handler, fallback="echo")
    # undo without prior apply -> "nothing to undo"
    detail = applier.undo(_prop(ProposalKind.REORDER_FALLBACK))
    assert "nothing to undo" in detail


def test_self_correct_undo_nothing() -> None:
    loop = _FakeLoop()
    applier = SelfCorrectApplier(loop)
    detail = applier.undo(_prop(ProposalKind.SELF_CORRECT))
    assert "nothing to undo" in detail


def test_apply_proposal_self_correct_without_loop() -> None:
    from universal_mind.core.errors import ErrorHandler
    from universal_mind.core.executive import ExecutionThrottle
    from universal_mind.prometheus.engine import ThrottleApplier

    handler = ErrorHandler()
    throttle = ThrottleApplier(ExecutionThrottle())
    fallback = FallbackOrderApplier(handler, fallback="echo")

    outcome = apply_proposal(_prop(ProposalKind.SELF_CORRECT), throttle, fallback, self_correct=None)
    assert "ignored" in outcome.detail


def test_apply_proposal_unsupported_kind() -> None:
    from universal_mind.core.errors import ErrorHandler
    from universal_mind.core.executive import ExecutionThrottle
    from universal_mind.prometheus.engine import ThrottleApplier

    handler = ErrorHandler()
    throttle = ThrottleApplier(ExecutionThrottle())
    fallback = FallbackOrderApplier(handler, fallback="echo")

    outcome = apply_proposal(_prop(ProposalKind.CHAMPION), throttle, fallback)
    assert "unsupported" in outcome.detail


# --- arete/audit_rubric ---


def test_audit_rubric_dimension_property() -> None:
    from universal_mind.arete.audit_rubric import ExternalRubric

    r = ExternalRubric()
    # scoring an empty evidence dict yields a low, honest score (rubric still works)
    card = r.score({})
    assert card.rubric_version == "1.0.0"
    assert isinstance(card.dimensions, tuple)


# --- core/self_code_audit ---


def test_self_code_audit_finds_orphaned_import(tmp_path: Path) -> None:

    from universal_mind.core.self_code_audit import scan_source

    (tmp_path / "bad.py").write_text(
        "from universal_mind.telemetry import thing\n", encoding="utf-8",  # type: ignore[unused-ignore]
    )
    findings = scan_source(Path(tmp_path))
    assert any(f.kind == "orphaned_import" for f in findings)