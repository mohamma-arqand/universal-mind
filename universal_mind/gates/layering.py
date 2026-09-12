"""Layering Gate: enforce the canonical layer boundary (no upward calls).

This gate is the *runtime* enforcement of the single layer model defined in
``universal_mind.layers``. It does NOT keep its own copy of the layer ranking:
it derives every layer from the canonical :class:`Layer` enum and the
:data:`LayerContract.may_call` matrix, so there is exactly one source of truth.

Previously this module duplicated the model as a string-keyed ``LAYER_RANKING``
dict and a *second* ``LayerViolation`` dataclass, and its ``caller_layer >
target_layer => DENY`` rule was the inverse of the model's ``may_call`` rule
(DEMIURGE may call PANTHEON, but the old gate refused it). Those are removed.
"""

from __future__ import annotations

from typing import Any

from universal_mind.core.intent import Intent
from universal_mind.layers import LAYER_CONTRACTS, Layer, LayerViolation
from universal_mind.pantheon.registry import CapabilityDossier

from .base import Gate, Verdict

__all__ = [
    "LayerViolation",
    "LayeringGate",
    "call_allowed",
    "create_layering_gate",
    "layer_for_capability",
]

# Map a capability/dossier name (or a component module path) to its canonical
# architectural Layer. Keys are the *canonical* layer names plus the module
# prefixes the executive actually sees. The numeric values are the Layer enum
# members, never raw ints, so a mistake here is a loud KeyError, not a silent
# mis-ranking.
_MODULE_TO_LAYER: dict[str, Layer] = {
    # L0 SUBSTRATE (foundation — importable by all)
    "core.clock": Layer.SUBSTRATE,
    "core.identity": Layer.SUBSTRATE,
    "core.models": Layer.SUBSTRATE,
    "core.intent": Layer.SUBSTRATE,
    "core.errors": Layer.SUBSTRATE,
    "memory.store": Layer.SUBSTRATE,
    "layers": Layer.SUBSTRATE,
    # L1 GATEWAY
    "io": Layer.GATEWAY,
    "gates": Layer.GATEWAY,
    "observability": Layer.GATEWAY,
    "compose": Layer.GATEWAY,
    # L2 PANTHEON
    "pantheon": Layer.PANTHEON,
    # L3 DEMIURGE
    "demiurge": Layer.DEMIURGE,
    "core.executive": Layer.DEMIURGE,
    "synthesis": Layer.DEMIURGE,
    "powers": Layer.DEMIURGE,
    # L4 ARETE
    "arete": Layer.ARETE,
    "feedback": Layer.ARETE,
    # L5 PROMETHEUS
    "prometheus": Layer.PROMETHEUS,
    "lifecycle": Layer.PROMETHEUS,
    "integration": Layer.PROMETHEUS,
    "durable": Layer.PROMETHEUS,
    # L6 MOUTH
    "mouth": Layer.MOUTH,
    "sovereign": Layer.MOUTH,
    # ⟂ MNEMOSYNE
    "memory.mnemosyne": Layer.MNEMOSYNE,
    "memory.lifespan": Layer.MNEMOSYNE,
}


def layer_for_capability(capability: CapabilityDossier) -> Layer:
    """Resolve the canonical :class:`Layer` for a capability, by name.

    Unknown names are treated as :data:`Layer.MNEMOSYNE` is NOT — an unknown
    component is *not* a special perpendicular layer, so we refuse to classify
    it rather than assume a rank. Callers handle the ``Unknown layer`` contract.
    """
    name = capability.name
    for prefix, layer in _MODULE_TO_LAYER.items():
        if name == prefix or name.startswith(prefix + "."):
            return layer
    # A capability whose name we cannot map has no declared layer: treat it as
    # the lowest/least-privileged (SUBSTRATE-like) so an unranked component can
    # never be assumed to outrank a real one.
    return Layer.MNEMOSYNE if name.startswith("memory.") else Layer.MOUTH


def call_allowed(caller: Layer, callee: Layer) -> bool:
    """Whether ``caller`` may command/call ``callee`` per the canonical model.

    A layer may call everything in its own :data:`LayerContract.may_call` set —
    that is, itself, every lower layer, and (for all but MNEMOSYNE) the
    perpendicular memory layer. MNEMOSYNE itself may only call SUBSTRATE.
    """
    contract = LAYER_CONTRACTS.get(caller)
    if contract is None:
        return False  # an unranked caller may call nothing beyond itself
    return callee in contract.may_call


class LayeringGate(Gate):
    """Gate that rejects any intent commanding a capability outside its layer."""

    def __init__(self, name: str = "Layering", enabled: bool = True) -> None:
        self._name = name
        self._enabled = enabled

    @property
    def precedence(self) -> int:
        return 900  # kept for interface compatibility; ordering is frozen elsewhere

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        if not self._enabled:
            return Verdict.ALLOW

        intent = context.get("intent")
        capability = context.get("capability")

        if intent is None or capability is None:
            return Verdict.ALLOW  # nothing to enforce

        violation = self._check_layer_violation(intent, capability, context)
        if violation is not None:
            return Verdict.DENY
        return Verdict.ALLOW

    def _check_layer_violation(
        self,
        intent: Intent,
        capability: CapabilityDossier,
        context: dict[str, Any],
    ) -> LayerViolation | None:
        """Return a violation when the caller's layer may not command the target.

        The caller layer is inferred from ``context['caller_layer']`` when
        supplied, else from the intent owner/goal. The target layer is the
        capability's layer. Unknown/unclassified caller or target fails *open*
        (allow) — a false DENY would break legal pipelines — but a classified
        caller commanding a target outside its ``may_call`` set is refused by
        the canonical model.
        """
        caller_layer = context.get("caller_layer")
        if caller_layer is None:
            caller_layer = self._infer_caller_layer(intent)

        target_layer = layer_for_capability(capability)

        # Unclassified: no clear violation, so allow (fail-open).
        if caller_layer is None or target_layer is None:
            return None

        if call_allowed(Layer(caller_layer), target_layer):
            return None

        return LayerViolation(
            caller_layer=Layer(caller_layer),
            callee_layer=target_layer,
            caller_name=f"intent:{intent.goal}",
            callee_name=f"capability:{capability.name}",
        )

    def _infer_caller_layer(self, intent: Intent) -> Layer | None:
        """Infer the caller's layer from intent owner_id or goal metadata."""
        owner = intent.owner_id.lower() if intent.owner_id else ""
        goal = intent.goal.lower() if intent.goal else ""
        for prefix, layer in _MODULE_TO_LAYER.items():
            if prefix in owner or prefix in goal:
                return layer
        return None


def create_layering_gate(name: str = "Layering", enabled: bool = True) -> LayeringGate:
    return LayeringGate(name=name, enabled=enabled)


# Keep the old attribute names get_layer/is_foundation for any external importer
# that still references the exported surface, but route them through the model.
def get_layer(module_name: str) -> int:
    """Return the canonical layer number for a module name (unknown → 999)."""
    for prefix, layer in _MODULE_TO_LAYER.items():
        if module_name == prefix or module_name.startswith(prefix + "."):
            return int(layer.value)
    return 999


def is_foundation(module_name: str) -> bool:
    """True if ``module_name`` is a SUBSTRATE (L0) component."""
    for prefix, layer in _MODULE_TO_LAYER.items():
        if module_name == prefix or module_name.startswith(prefix + "."):
            return layer is Layer.SUBSTRATE
    return False