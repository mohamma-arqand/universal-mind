"""Direct coverage for LayeringGate, including the layer-violation fix.

The gate's enforcement body (caller_layer > target_layer → DENY) was effectively
dead: `if caller_layer <= 3e7` short-circuited every classified caller into the
"foundation, always allow" branch, so NO downward-command was ever blocked. This
regression test locks the fix AND covers the remaining branches.
"""

from __future__ import annotations

from universal_mind.core.intent import Determinism, Intent
from universal_mind.gates.base import Verdict
from universal_mind.gates.layering import (
    LayeringGate,
    LayerViolation,
    create_layering_gate,
    get_layer,
    is_foundation,
)
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


def test_downward_command_is_denied() -> None:
    """A lower layer (mouth, 6) commanding a higher layer (arete, 4) is DENY."""
    gate = LayeringGate()
    intent = _intent("mouth", "do a task")  # no layer-word in goal -> infer from owner
    cap = _dossier("arete.standard")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.DENY


def test_same_or_upward_command_is_allowed() -> None:
    gate = LayeringGate()
    # arete (4) commanding mouth (6): caller is higher, target lower -> allowed
    intent = _intent("arete", "do a task")
    cap = _dossier("mouth.commit")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_unknown_caller_fails_open() -> None:
    gate = LayeringGate()
    intent = _intent("some-external-system", "do a task")
    cap = _dossier("arete.standard")
    # unknown caller (999) + known target -> fail-open (no clear violation)
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_foundation_target_allows_any_caller() -> None:
    gate = LayeringGate()
    intent = _intent("mouth", "do a task")
    cap = _dossier("core.intent")  # foundation (L0)
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_disabled_gate_always_allows() -> None:
    gate = LayeringGate(enabled=False)
    intent = _intent("mouth", "do a task")
    cap = _dossier("arete.standard")
    assert gate.evaluate({"intent": intent, "capability": cap}) == Verdict.ALLOW


def test_missing_intent_or_capability_allows() -> None:
    gate = LayeringGate()
    assert gate.evaluate({}) == Verdict.ALLOW
    assert gate.evaluate({"intent": _intent("mouth")}) == Verdict.ALLOW


def test_violation_object_carries_layers() -> None:
    gate = LayeringGate()
    v = gate._check_layer_violation(_intent("mouth"), _dossier("arete.standard"), {})
    assert isinstance(v, LayerViolation)
    assert v.action_layer == 6 and v.target_layer == 4


def test_get_layer_and_is_foundation() -> None:
    assert get_layer("io.gateway") == 1
    assert get_layer("unknown.thing") == 999
    assert is_foundation("core.intent") is True
    assert is_foundation("arete.standard") is False


def test_create_layering_gate_factory() -> None:
    gate = create_layering_gate(enabled=False)
    assert gate.name == "Layering"
    assert gate.precedence == 900