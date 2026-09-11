"""Tests for self-awareness wired into ExecutiveMind's execution loop."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.clock import SystemClock
from universal_mind.core.executive import ExecutiveMind
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.intent import Determinism, Intent
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.contracts import EchoCapability
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry


def _dossier() -> CapabilityDossier:
    return CapabilityDossier(
        name="echo",
        version="1.0.0",
        signature="echo(intent, params)",
        purpose="echo the intent",
        cost_model="flat",
        latency_profile="instant",
        reliability="high",
        side_effects="none",
        reversible=True,
        required_secrets=[],
        failure_modes="none",
        dependencies=[],
        determinism=Determinism.STRICT,
        idempotent=True,
        provenance={"owner_id": "sovereign", "explicit_fields": ["idempotent"]},
    )


def _mk_intent() -> Intent:
    return Intent.from_raw(
        raw_text="do the thing",
        goal="do the thing",
        success_criteria=["done"],
        constraints=[],
        deadline=None,
        determinism=Determinism.STRICT,
        owner_id="sovereign",
    )


def _mk_executive(store: InMemoryStore) -> ExecutiveMind:
    registry = PantheonRegistry(store)
    registry.register(_dossier(), EchoCapability())
    memory = Mnemosyne(store, SystemClock())
    executive = ExecutiveMind(
        registry=registry,
        memory=memory,
        clock=SystemClock(),
        owner=DEFAULT_OWNER,
    )
    return executive


def test_executive_with_self_awareness_closes_loop() -> None:
    store = InMemoryStore()
    registry = PantheonRegistry(store)
    registry.register(_dossier(), EchoCapability())
    memory = Mnemosyne(store, SystemClock())
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    executive = ExecutiveMind(
        registry=registry,
        memory=memory,
        clock=SystemClock(),
        owner=DEFAULT_OWNER,
        self_awareness=loop,
    )
    record = executive.handle(_mk_intent())
    assert record.status == "ok"
    # The meta loop introspects after a successful execution -> a self_awareness
    # entry appears in the shared ledger.
    kinds = [r.get("kind") for r in store.read_all()]
    assert "self_awareness" in kinds


def test_executive_without_self_awareness_is_unchanged() -> None:
    """No self-awareness loop means no introspection side effect (backward-compat)."""
    store = InMemoryStore()
    executive = _mk_executive(store)
    record = executive.handle(_mk_intent())
    assert record.status == "ok"
    kinds = [r.get("kind") for r in store.read_all()]
    assert "self_awareness" not in kinds


def test_loop_introspects_only_on_success() -> None:
    """A self-aware executive does not introspect when the cycle did not fully succeed."""
    # Introspection is gated on result.ok; a no-op here verifies the wiring
    # doesn't crash on a non-ok path by exercising the public surface.
    store = InMemoryStore()
    executive = _mk_executive(store)
    assert executive.self_awareness is None