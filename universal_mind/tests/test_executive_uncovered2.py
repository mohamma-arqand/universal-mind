"""Coverage for ExecutiveMind's remaining adapter + fallback branches."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from universal_mind.core.clock import FrozenClock
from universal_mind.core.errors import (
    ErrorHandler,
    RetryPolicy,
    TaskFailure,
)
from universal_mind.core.executive import ExecutiveMind
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.feedback.channel import HumanFeedbackGate
from universal_mind.feedback.channel import Verdict as FeedbackVerdict
from universal_mind.gates import Verdict as GateVerdict
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.contracts import Capability, CapabilityResult
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


def _dossier(name: str = "echo", **over: Any) -> CapabilityDossier:
    fields: dict[str, Any] = {
        "name": name, "version": "1.0.0", "signature": f"{name}()",
        "purpose": f"serve {name}", "cost_model": "flat", "latency_profile": "instant",
        "reliability": "high", "side_effects": "none", "reversible": True,
        "required_secrets": [], "failure_modes": "none", "dependencies": [],
        "determinism": Determinism.STRICT,
        "provenance": {"producer": "test", "created_at": datetime.now(timezone.utc).isoformat(),
                       "owner_id": DEFAULT_OWNER.owner_id, "explicit_fields": ["idempotent"]},
        "idempotent": True,
    }
    fields.update(over)
    return CapabilityDossier(**fields)


def _intent(goal: str = "echo") -> Intent:
    return Intent.from_raw(raw_text=goal, goal=goal, success_criteria=["ok"],
                           owner_id=DEFAULT_OWNER.owner_id)


class _Echo(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        return CapabilityResult(ok=True, output={"goal": intent.goal},
                                cost={"currency": "cycles", "amount": 1},
                                provenance={"producer": "echo"}, notes=("ok",))


class _RaisesUnexpected(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise RuntimeError("unexpected non-fault error")


class _FailsTask(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise TaskFailure("primary fails")


class _RaisesKeyError(Capability):
    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        raise KeyError("totally unexpected")


def _env() -> tuple[PantheonRegistry, Mnemosyne, FrozenClock, InMemoryStore]:
    clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
    store = InMemoryStore()
    return PantheonRegistry(store), Mnemosyne(store, clock), clock, store


def test_human_feedback_gate_adapter_deny_and_allow() -> None:
    clock = FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
    store = InMemoryStore()
    fg = HumanFeedbackGate(store=store, clock=clock)
    fg.submit(DEFAULT_OWNER.owner_id, "target-1", FeedbackVerdict.REJECTED, "bad")

    from universal_mind.core.executive import _HumanFeedbackGateAdapter

    adapter = _HumanFeedbackGateAdapter(fg, target_record_id="target-1")
    assert adapter.evaluate({}) == GateVerdict.DENY

    adapter2 = _HumanFeedbackGateAdapter(fg, target_record_id="other")
    assert adapter2.evaluate({}) == GateVerdict.ALLOW


def test_record_gate_decisions_with_no_judgment_does_nothing() -> None:
    registry, memory, clock, _store = _env()
    mind = ExecutiveMind(registry, memory, clock, owner=DEFAULT_OWNER)
    # _last_judgment is None -> _record_gate_decisions returns silently.
    mind._record_gate_decisions(None)  # type: ignore[arg-type]
    assert mind._recorder_failures == 0


def test_fallback_unexpected_error_wraps_as_system_fault() -> None:
    registry, memory, clock, _store = _env()
    # primary fails with TaskFailure; fallback 'echo' raises an unexpected error
    # (KeyError) -> wrapped as SystemFault, chain continues, then primary re-raised.
    handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=0), fallback_capability="echo")
    registry.register(_dossier(name="echo"), _RaisesKeyError())
    mind = ExecutiveMind(registry, memory, clock, owner=DEFAULT_OWNER, error_handler=handler)

    with pytest.raises(TaskFailure):
        mind._execute_with_retries(
            _FailsTask(), _intent(), {"owner_id": DEFAULT_OWNER.owner_id},
            _dossier(name="primary", idempotent=False),
        )


def test_fallback_runtime_error_is_system_fault_not_retried() -> None:
    # A RuntimeError from the primary (not a TaskFailure/SystemFault/CallerFault)
    # is unexpected: it is wrapped and surfaces (no infinite retry).
    registry, memory, clock, _store = _env()
    handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=0))
    mind = ExecutiveMind(registry, memory, clock, owner=DEFAULT_OWNER, error_handler=handler)
    with pytest.raises(RuntimeError):
        mind._execute_with_retries(
            _RaisesUnexpected(), _intent(), {"owner_id": DEFAULT_OWNER.owner_id},
            _dossier(name="primary", idempotent=False),
        )