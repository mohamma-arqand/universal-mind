"""Direct coverage for LayeringGate — enforcing the CANONICAL layer model.

The canonical model (universal_mind.layers) says a layer may call everything in
its own `LayerContract.may_call` set: itself, every lower layer, and (for all
but MNEMOSYNE) the perpendicular memory layer. Layer *number* is ascending with
privilege: SUBSTRATE=0 (lowest), MOUTH=6 (highest), MNEMOSYNE=7 (perpendicular).

So a *higher* layer may command a *lower* one, never the reverse. MOUTH (6) may
command ARETE (4); ARETE (4) may NOT command MOUTH (6).

Earlier this gate used an inverted `caller_layer > target_layer => DENY` rule and
a duplicated string ranking; both are gone. These tests lock the correct model.
"""

from __future__ import annotations

from universal_mind.core.intent import Determinism, Intent
from universal_mind.gates.base import Verdict
from universal_mind.gates.layering import (
    LayeringGate,
    LayerViolation,
    call_allowed,
    create_layering_gate,
    get_layer,
    is_foundation,
    layer_for_capability,
)
from universal_mind.layers import Layer
from universal_mind.pantheon.registry import CapabilityDossier


def _intent(owner_id: str, goal: str = "do a task") -> Intent:
    return Intent(
        raw_text=goal, goal=goal, success_criteria=["y"], constraints=[],
        deadline=None, determinism=Determinism.STRICT, owner_id=owner_id,
    )


def _dossier(name: str) -> CapabilityDossier:
    return CapabilityDossier(
        name=name, version="1.0.0", signature="x()", purpose="x", cost_model="flat",
        latency_profile="instant", reliability="high", side_effects="none",
        reversible=True, required_secrets=[], failure_modes="none",
        dependencies=[], determinism=Determinism.STRICT,
        provenance={"explicit_fields": ["idempotent"]}, idempotent=True,
    )


def test_higher_layer_commands_lower() -> None:
    """MOUTH (6) may command ARETE (4) — it is in MOUTH's may_call set."""
    gate = LayeringGate()
    intent = _intent("mouth", "do a task")
    cap = _dossier("arete.standard")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_lower_layer_cannot_command_higher() -> None:
    """ARETE (4) may NOT command MOUTH (6) — the canonical model forbids it."""
    gate = LayeringGate()
    intent = _intent("arete", "do a task")
    cap = _dossier("mouth.commit")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.DENY


def test_call_allowed_matches_canonical_matrix() -> None:
    # spot-check the canonical may_call matrix
    assert call_allowed(Layer.DEMIURGE, Layer.PANTHEON) is True   # downward
    assert call_allowed(Layer.PANTHEON, Layer.DEMIURGE) is False  # upward
    assert call_allowed(Layer.MNEMOSYNE, Layer.SUBSTRATE) is True  # memory→substrate
    assert call_allowed(Layer.MNEMOSYNE, Layer.ARETE) is False     # memory→up


def test_layer_for_capability_maps_names() -> None:
    assert layer_for_capability(_dossier("io.gateway")) is Layer.GATEWAY
    assert layer_for_capability(_dossier("arete.standard")) is Layer.ARETE
    assert layer_for_capability(_dossier("core.intent")) is Layer.SUBSTRATE
    assert layer_for_capability(_dossier("memory.mnemosyne")) is Layer.MNEMOSYNE


def test_unknown_caller_fails_open() -> None:
    gate = LayeringGate()
    intent = _intent("some-external-system", "do a task")
    cap = _dossier("arete.standard")
    # unknown caller (no layer prefix) -> no clear violation -> allow (fail-open)
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_foundation_target_allows_any_caller() -> None:
    gate = LayeringGate()
    intent = _intent("mouth", "do a task")
    cap = _dossier("core.intent")  # SUBSTRATE is in every layer's may_call
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_disabled_gate_always_allows() -> None:
    gate = LayeringGate(enabled=False)
    intent = _intent("arete", "do a task")
    cap = _dossier("mouth.commit")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_missing_intent_or_capability_allows() -> None:
    gate = LayeringGate()
    assert gate.evaluate({}) == Verdict.ALLOW
    assert gate.evaluate({"intent": _intent("mouth")}) == Verdict.ALLOW


def test_violation_object_is_real_exception() -> None:
    gate = LayeringGate()
    v = gate._check_layer_violation(_intent("arete"), _dossier("mouth.commit"), {})
    assert isinstance(v, LayerViolation)
    # LayerViolation is now the canonical one from layers.py — a real exception
    import universal_mind.core.errors as _e

    assert isinstance(v, _e.UniversalMindError)
    assert v.caller_layer is Layer.ARETE
    assert v.callee_layer is Layer.MOUTH


def test_get_layer_and_is_foundation() -> None:
    assert get_layer("io.gateway") == 1
    assert get_layer("unknown.thing") == 999
    assert is_foundation("core.intent") is True
    assert is_foundation("arete.standard") is False


def test_create_layering_gate_factory() -> None:
    gate = create_layering_gate(enabled=False)
    assert gate.name == "Layering"
    assert gate.precedence == 900