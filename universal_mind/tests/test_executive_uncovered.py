"""Direct coverage for the Executive Mind's uncovered logic branches.

The executive is the heart of the system but huge swaths (throttle caller-fault
exclusion, risk-assessor branches, fallback chain, fault recording, capability
selection fallback) were only indirectly exercised. These tests target exactly
those lines, proving behavior and catching regressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from universal_mind.core.clock import FrozenClock
from universal_mind.core.errors import (
    CallerFault,
    ErrorHandler,
    RetryPolicy,
    SystemFault,
    TaskFailure,
)
from universal_mind.core.executive import (
    Decision,
    DefaultRiskPolicy,
    ExecutionThrottle,
    ExecutiveMind,
    HumanFeedbackGateWrapper,
    RiskAssessor,
    RiskGate,
    RiskPolicy,
    StrategicDecision,
    StrategicGate,
    ThrottleGate,
    _PolicyGateAdapter,
    _RiskGateAdapter,
)
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.feedback.channel import HumanFeedbackGate
from universal_mind.feedback.channel import Verdict as FeedbackVerdict
from universal_mind.gates import Verdict as GateVerdict
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.contracts import Capability, CapabilityResult
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


def _intent(goal: str = "echo", determinism: Determinism = Determinism.STRICT) -> Intent:
    return Intent.from_raw(
        raw_text=goal,
        goal=goal,
        success_criteria=["ok"],
        determinism=determinism,
        owner_id=DEFAULT_OWNER.owner_id,
    )


def _dossier(name: str = "echo", determinism: Determinism = Determinism.STRICT, **over: Any) -> CapabilityDossier:
    fields: dict[str, Any] = {
        "name": name,
        "version": "1.0.0",
        "signature": f"{name}(intent, params)",
        "purpose": f"echo {name}",
        "cost_model": "flat",
        "latency_profile": "instant",
        "reliability": "high",
        "side_effects": "none",
        "reversible": True,
        "required_secrets": [],
        "failure_modes": "none",
        "dependencies": [],
        "determinism": determinism,
        "provenance": {"producer": "test", "created_at": datetime.now(timezone.utc).isoformat(),
                       "owner_id": DEFAULT_OWNER.owner_id, "explicit_fields": ["idempotent"]},
        "idempotent": True,
    }
    fields.update(over)
    return CapabilityDossier(**fields)


class _Echo(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        return CapabilityResult(
            ok=True, output={"goal": intent.goal}, cost={"currency": "cycles", "amount": 1},
            provenance={"producer": "echo"}, notes=("ok",),
        )


class _FailTask(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise TaskFailure("task failure")


class _FailSystem(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise SystemFault("system fault")


class _FailCaller(Capability):
    def validate_intent(self, intent: Intent) -> None:
        raise CallerFault("caller fault")

    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise CallerFault("caller fault")


@dataclass
class _Env:
    clock: FrozenClock
    store: InMemoryStore
    memory: Mnemosyne
    registry: PantheonRegistry

    @classmethod
    def make(cls) -> _Env:
        clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        store = InMemoryStore()
        return cls(clock, store, Mnemosyne(store, clock), PantheonRegistry(store))


# --- ExecutionThrottle.should_allow (caller-fault exclusion, max_concurrent) ---


def test_throttle_excludes_caller_faults_from_error_rate() -> None:
    t = ExecutionThrottle(max_concurrent=100, error_rate_threshold=0.1)
    # 5 errors, 4 of them caller faults -> effective error rate 1/10 = 0.1 -> allowed
    assert t.should_allow(recent_errors=5, recent_executions=10, caller_faults=4) is True


def test_throttle_blocks_when_error_rate_too_high() -> None:
    t = ExecutionThrottle(max_concurrent=100, error_rate_threshold=0.1)
    # 5 real errors, 0 caller faults -> 5/10 = 0.5 > 0.1 -> blocked
    assert t.should_allow(recent_errors=5, recent_executions=10, caller_faults=0) is False


def test_throttle_blocks_when_max_concurrent_reached() -> None:
    t = ExecutionThrottle(max_concurrent=10, error_rate_threshold=0.1)
    assert t.should_allow(recent_errors=0, recent_executions=10, caller_faults=0) is False


def test_throttle_caller_faults_cannot_exceed_errors() -> None:
    t = ExecutionThrottle(max_concurrent=100, error_rate_threshold=0.1)
    # caller_faults > errors is clamped to zero effective errors via max(0, ...)
    assert t.should_allow(recent_errors=1, recent_executions=1, caller_faults=5) is True


# --- RiskAssessor.assess (all branches) ---


def test_risk_assessor_all_levels() -> None:
    a = RiskAssessor()
    high = a.assess(_intent(), _Echo(), _dossier(reliability="low"))
    med_modes = a.assess(_intent(), _Echo(), _dossier(failure_modes="timeout"))
    med_determ = a.assess(_intent(determinism=Determinism.CREATIVE), _Echo(), _dossier())
    low = a.assess(_intent(), _Echo(), _dossier())
    assert high == "high"
    assert med_modes == "medium"
    assert med_determ == "medium"
    assert low == "low"


# --- DefaultRiskPolicy.allows (boolean precedence, medium/low blocks) ---


def test_default_risk_policy_high_reversible_strict() -> None:
    p = DefaultRiskPolicy()
    d = _dossier(reversible=True)
    assert p.allows("high", d, _intent(determinism=Determinism.STRICT)) is True


def test_default_risk_policy_high_blocks_when_not_reversible() -> None:
    p = DefaultRiskPolicy()
    d = _dossier(reversible=False)
    assert p.allows("high", d, _intent()) is False


def test_default_risk_policy_medium_and_low_block_overrides() -> None:
    p = DefaultRiskPolicy(RiskPolicy(medium_risk_blocks=True, low_risk_blocks=True))
    assert p.allows("medium", None, _intent()) is False
    assert p.allows("low", None, _intent()) is False


def test_default_risk_policy_medium_low_default_proceed() -> None:
    p = DefaultRiskPolicy()
    assert p.allows("medium", None, _intent()) is True
    assert p.allows("low", None, _intent()) is True


# --- ThrottleGate + _fault_metrics ---


def test_throttle_gate_fault_metrics_and_block() -> None:
    env = _Env.make()
    # seed: 1 fault (caller) + 2 executions
    env.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind="fault",
                      payload={"fault_class": "caller_fault"},
                      provenance={"producer": "test"})
    env.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind="intent_received",
                      payload={}, provenance={"producer": "test"})
    env.memory.record(owner_id=DEFAULT_OWNER.owner_id, kind="capability_selected",
                      payload={}, provenance={"producer": "test"})

    total, execs, callers = ThrottleGate._fault_metrics(env.memory, DEFAULT_OWNER.owner_id)
    assert (total, execs, callers) == (1, 2, 1)

    # max_concurrent=2 -> executions(2) >= 2 -> blocked
    gate = ThrottleGate(ExecutionThrottle(max_concurrent=2), env.memory, DEFAULT_OWNER.owner_id)
    decision = gate.evaluate(_intent(), {})
    assert decision.decision == Decision.BLOCK
    assert "Throttled" in (decision.reason or "")


def test_throttle_gate_proceeds_when_ok() -> None:
    env = _Env.make()
    gate = ThrottleGate(ExecutionThrottle(max_concurrent=100), env.memory, DEFAULT_OWNER.owner_id)
    assert gate.evaluate(_intent(), {}).decision == Decision.PROCEED


# --- RiskGate + HumanFeedbackGateWrapper ---


def test_risk_gate_blocks_high_risk_when_irreversible() -> None:
    # reliability low -> risk 'high'; not reversible -> policy blocks
    sel = lambda: (_dossier(reliability="low", reversible=False), _Echo())
    gate = RiskGate(RiskAssessor(), sel, DefaultRiskPolicy())
    decision = gate.evaluate(_intent(), {})
    assert decision.decision == Decision.BLOCK
    assert "high" in (decision.reason or "")


def test_risk_gate_proceeds_high_risk_reversible_strict() -> None:
    # high risk but reversible + strict determinism -> allowed (the exception)
    sel = lambda: (_dossier(reliability="low", reversible=True), _Echo())
    gate = RiskGate(RiskAssessor(), sel, DefaultRiskPolicy())
    assert gate.evaluate(_intent(), {}).decision == Decision.PROCEED


def test_risk_gate_proceeds_low_risk() -> None:
    sel = lambda: (_dossier(reliability="high"), _Echo())
    gate = RiskGate(RiskAssessor(), sel, DefaultRiskPolicy())
    decision = gate.evaluate(_intent(), {})
    assert decision.decision == Decision.PROCEED


def test_human_feedback_gate_wrapper_blocks_target() -> None:
    env = _Env.make()
    fg = HumanFeedbackGate(store=env.store, clock=env.clock)
    fg.submit(DEFAULT_OWNER.owner_id, "target-1", FeedbackVerdict.REJECTED, "bad")
    wrapper = HumanFeedbackGateWrapper(fg)
    assert wrapper.evaluate(_intent(), {"target_record_id": "target-1"}).decision == Decision.BLOCK
    assert wrapper.evaluate(_intent(), {"target_record_id": "other"}).decision == Decision.PROCEED


# --- CompositeStrategicGate via executive pipeline (REDIRECT, block, fault) ---


class _RedirectGate(StrategicGate):
    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        return StrategicDecision(decision=Decision.REDIRECT, redirect_capability="echo", reason="go there")


def test_policy_gate_adapter_defers_on_redirect() -> None:
    adapter = _PolicyGateAdapter(_RedirectGate(), name="Policy")
    verdict = adapter.evaluate({"intent": _intent()})
    assert verdict == GateVerdict.DEFER


def test_policy_gate_adapter_raises_without_intent() -> None:
    adapter = _PolicyGateAdapter(StrategicGate(), name="Policy")
    with pytest.raises(ValueError):
        adapter.evaluate({})


def test_risk_gate_adapter_raises_without_intent() -> None:
    sel = lambda: (_dossier(), _Echo())
    adapter = _RiskGateAdapter(RiskAssessor(), sel, DefaultRiskPolicy(), name="Risk")
    with pytest.raises(ValueError):
        adapter.evaluate({})


def test_risk_gate_adapter_allows_and_denies() -> None:
    low_dossier = _dossier(reliability="high")
    sel_low = lambda: (low_dossier, _Echo())
    adapter = _RiskGateAdapter(RiskAssessor(), sel_low, DefaultRiskPolicy(), name="Risk")
    ctx: dict[str, Any] = {"intent": _intent()}
    assert adapter.evaluate(ctx) == GateVerdict.ALLOW
    assert ctx["risk_level"] == "low"
    assert ctx["dossier"] is low_dossier


def test_find_capability_by_name() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="alpha"), _Echo())
    env.registry.register(_dossier(name="beta"), _Echo())
    mind = _mind(env)
    assert mind._find_capability_by_name("beta") is not None
    assert mind._find_capability_by_name("beta").name == "beta"  # type: ignore[union-attr]
    assert mind._find_capability_by_name("nope") is None


# --- _select_capability fallbacks (substring + first dossier + none) ---


def _mind(env: _Env, **kw: Any) -> ExecutiveMind:
    return ExecutiveMind(env.registry, env.memory, env.clock, DEFAULT_OWNER, **kw)


def test_select_capability_exact_then_substring_then_first() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="alpha", purpose="first thing"), _Echo())
    env.registry.register(_dossier(name="beta", purpose="second thing"), _Echo())
    mind = _mind(env)
    # exact name match
    assert mind._select_capability(_intent(goal="beta")).name == "beta"
    # substring match via purpose
    assert mind._select_capability(_intent(goal="second")).name == "beta"
    # fallback: no match -> first dossier
    assert mind._select_capability(_intent(goal="zzz")).name == "alpha"


def test_select_capability_no_dossiers_raises_task_failure() -> None:
    env = _Env.make()
    mind = _mind(env)
    with pytest.raises(TaskFailure):
        mind._select_capability(_intent())


# --- handle(): fault branches get recorded and re-raised ---


def test_handle_caller_fault_is_recorded_and_raised() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="echo"), _FailCaller())
    mind = _mind(env)
    with pytest.raises(CallerFault):
        mind.handle(_intent(goal="echo"))
    kinds = [r["kind"] for r in env.store.read_all()]
    assert "fault" in kinds


def test_handle_task_failure_falls_back_and_then_raises() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="echo"), _FailTask())
    mind = _mind(env)
    with pytest.raises(TaskFailure):
        mind.handle(_intent(goal="echo"))
    assert any(r["kind"] == "fault" for r in env.store.read_all())


def test_handle_success_records_cycle() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="echo"), _Echo())
    mind = _mind(env)
    rec = mind.handle(_intent(goal="echo"))
    assert rec.status == "ok"
    kinds = [r["kind"] for r in env.store.read_all()]
    assert "capability_result" in kinds


def test_execute_with_retries_system_fault_not_retried() -> None:
    env = _Env.make()
    env.registry.register(_dossier(name="echo", idempotent=True), _FailSystem())
    mind = _mind(env)
    with pytest.raises(SystemFault):
        mind._execute_with_retries(_FailSystem(), _intent(), {"owner_id": DEFAULT_OWNER.owner_id},
                                   _dossier(name="echo", idempotent=True))


def test_execute_with_retries_fallback_chain_used() -> None:
    env = _Env.make()
    # primary fails, fallback echo succeeds
    handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=0), fallback_capability="echo")
    # register the fallback capability under name 'echo'
    env.registry.register(_dossier(name="echo"), _Echo())
    mind = _mind(env, error_handler=handler)
    result = mind._execute_with_retries(_FailTask(), _intent(), {"owner_id": DEFAULT_OWNER.owner_id},
                                        _dossier(name="primary", idempotent=False))
    assert result.ok is True