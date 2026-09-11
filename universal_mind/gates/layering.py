"""Layering Gate: enforces layer boundaries (no upward commands)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.core.intent import Intent
from universal_mind.pantheon.registry import CapabilityDossier

from .base import Gate, Verdict


@dataclass(frozen=True)
class LayerViolation:
    """A layering violation detected by LayeringGate."""
    action_layer: int
    target_layer: int
    action: str
    target: str
    message: str


# Layer ranking (lower number = higher layer = more privileged)
# Rule: a module at layer N can only command layers >= N (same or lower)
# i.e., cannot import/call upward to layers with smaller numbers.
#
# Aligned with the authoritative model in universal_mind/layers.py (Layer enum):
# SUBSTRATE=0, GATEWAY=1, PANTHEON=2, DEMIURGE=3, ARETE=4, PROMETHEUS=5,
# MOUTH=6, MNEMOSYNE=7 (the ⟂ layer, callable by all, calls only SUBSTRATE).
LAYER_RANKING = {
    'io': 1,
    'pantheon': 2,
    'demiurge': 3,
    'arete': 4,
    'prometheus': 5,
    'mouth': 6,
    'memory.mnemosyne': 7,
    'memory.lifespan': 7,
    'sovereign': 6,
    'synthesis': 3,
    'lifecycle': 5,
    'integration': 5,
    'gates': 2,
    'core.executive': 3,
    'observability': 2,
    'core.clock': 0,
    'core.identity': 0,
    'core.models': 0,
    'core.intent': 0,
    'core.errors': 0,
    'memory.store': 0,
    'layers': 0,
    'powers': 3,
    'feedback': 4,
    'durable': 5,
    'compose': 3,
}

# Foundation modules (can be imported by anyone — the SUBSTRATE layer L0).
FOUNDATION_LAYERS = {
    'core.clock', 'core.identity', 'core.models', 'memory.store',
    'core.intent', 'core.errors', 'layers',
}


def get_layer(module_name: str) -> int:
    """Get layer number for a module. Unknown = 999 (lowest)."""
    for prefix, layer in LAYER_RANKING.items():
        if module_name == prefix or module_name.startswith(prefix + '.'):
            return layer
    return 999


def is_foundation(module_name: str) -> bool:
    return module_name in FOUNDATION_LAYERS


class LayeringGate(Gate):
    """Gate that rejects any action violating layer boundaries.

    Rule: A lower layer (higher number) must not command a higher layer
    (lower number). This gate checks the call stack to detect violations.

    Precedence: 900 (runs after PowerZero at 1000, before Risk at 600).
    """

    def __init__(
        self,
        name: str = "Layering",
        enabled: bool = True,
    ):
        # Name is fixed to "Layering" to match GATE_PRECEDENCE
        self._name = name
        self._enabled = enabled

    @property
    def precedence(self) -> int:
        return 900  # Not used anymore, but kept for interface compatibility

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        if not self._enabled:
            return Verdict.ALLOW

        intent = context.get('intent')
        capability = context.get('capability')

        if intent is None or capability is None:
            return Verdict.ALLOW  # Can't evaluate, allow

        # Check if this intent violates layer boundaries
        violation = self._check_layer_violation(intent, capability, context)
        if violation:
            return Verdict.DENY

        return Verdict.ALLOW

    def _check_layer_violation(
        self,
        intent: Intent,
        capability: CapabilityDossier,
        context: dict[str, Any]
    ) -> LayerViolation | None:
        """Check if intent from one layer commands a capability in a higher layer."""
        # Determine the layer of the caller (intent owner/component)
        # This is heuristic - in practice, you'd pass caller_layer in context
        caller_layer = context.get('caller_layer')
        if caller_layer is None:
            # Try to infer from owner_id or goal
            caller_layer = self._infer_caller_layer(intent)

        # Determine target layer from capability
        target_layer = get_layer(capability.name)

        # Unknown caller or target cannot be classified as a *clear* violation:
        # fail-open (allow) rather than false-positive-deny, matching the gate's
        # historical behavior when context carries no layer signal.
        if caller_layer == 999 or target_layer == 999:
            return None

        # Foundation layers (SUBSTRATE, L0) may be imported by anyone.
        if is_foundation(capability.name) or caller_layer == 0:
            return None

        # Violation: caller at lower layer (higher number) commanding higher layer
        # (lower number).
        if caller_layer > target_layer:
            return LayerViolation(
                action_layer=caller_layer,
                target_layer=target_layer,
                action=f"intent:{intent.goal}",
                target=f"capability:{capability.name}",
                message=(
                    f"Layer violation: layer {caller_layer} (lower) "
                    f"cannot command layer {target_layer} (higher)"
                )
            )

        return None

    def _infer_caller_layer(self, intent: Intent) -> int:
        """Infer caller layer from intent metadata."""
        # Heuristic: if owner_id or goal contains layer hints
        owner = intent.owner_id.lower() if intent.owner_id else ""
        goal = intent.goal.lower() if intent.goal else ""

        # Check for known layer prefixes
        for prefix, layer in LAYER_RANKING.items():
            if prefix in owner or prefix in goal:
                return layer

        return 999  # Unknown = lowest layer (most restricted)


# Convenience: create a layering gate for standard use
def create_layering_gate(
    name: str = "Layering",
    enabled: bool = True,
) -> LayeringGate:
    return LayeringGate(name=name, enabled=enabled)