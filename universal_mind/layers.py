"""Layer contracts for universal_mind architecture.

L3 DEMIURGE / L2 PANTHEON / L1 GATEWAY / L0 SUBSTRATE / MNEMOSYNE

Rule enforced in code: a component may call LAYER-1 or its own layer.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from functools import wraps
from typing import Any, TypeVar

from .core.errors import UniversalMindError


class Layer(IntEnum):
    """Architectural layers from lowest (substrate) to highest (mouth).

    Mirrors the charter's six-layer stack L0..L6 + the perpendicular MNEMOSYNE:
    L0 SUBSTRATE, L1 GATEWAY, L2 PANTHEON, L3 DEMIURGE, L4 ARETĒ, L5 PROMETHEUS,
    L6 MOUTH, and ⟂ MNEMOSYNE (callable by any layer, calls only SUBSTRATE).
    """

    SUBSTRATE = 0
    GATEWAY = 1
    PANTHEON = 2
    DEMIURGE = 3
    ARETE = 4
    PROMETHEUS = 5
    MOUTH = 6
    MNEMOSYNE = 7  # Special ⟂ layer: callable by any layer, calls only SUBSTRATE


class LayerViolation(UniversalMindError):
    """Raised when a component calls outside its allowed layer range."""

    def __init__(self, caller_layer: Layer, callee_layer: Layer, caller_name: str, callee_name: str) -> None:
        self.caller_layer = caller_layer
        self.callee_layer = callee_layer
        self.caller_name = caller_name
        self.callee_name = callee_name
        super().__init__(
            f"Layer violation: {caller_name} (layer {caller_layer.name}={caller_layer.value}) "
            f"cannot call {callee_name} (layer {callee_layer.name}={callee_layer.value}). "
            f"Allowed: own layer ({caller_layer.name}) or LAYER-1 ({Layer(caller_layer.value - 1).name if caller_layer.value > 0 else 'none'})."
        )


def assert_call_allowed(caller: Any, callee: Any) -> None:
    """Assert that caller is allowed to call callee based on layer rules.

    A component may call:
    - Its own layer
    - LAYER-1 (the layer directly below it)
    - MNEMOSYNE layer (special: can be called by any layer)

    Args:
        caller: Object with LAYER classvar
        callee: Object with LAYER classvar

    Raises:
        LayerViolation: If the call violates layer rules
    """
    caller_layer = getattr(caller, 'LAYER', None)
    callee_layer = getattr(callee, 'LAYER', None)

    if caller_layer is None or callee_layer is None:
        raise LayerViolation(
            Layer.SUBSTRATE, Layer.SUBSTRATE,
            type(caller).__name__, type(callee).__name__
        )

    # MNEMOSYNE is special: can be called by any layer
    if callee_layer == Layer.MNEMOSYNE:
        return

    # Same layer is allowed
    if caller_layer == callee_layer:
        return

    # LAYER-1 is allowed
    if caller_layer.value - 1 == callee_layer.value:
        return

    raise LayerViolation(caller_layer, callee_layer, type(caller).__name__, type(callee).__name__)


F = TypeVar('F', bound=Callable[..., Any])


def layered(func: F) -> F:
    """Decorator to enforce layer contracts on cross-layer entry points.

    Usage:
        @layered
        def my_method(self, other_component):
            assert_call_allowed(self, other_component)
            ...

    The decorated function's first argument (self) is treated as the caller,
    and the second argument (or first non-self arg) as the callee.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # args[0] is typically self (the caller)
        # args[1] is typically the callee component
        if len(args) >= 2:
            caller = args[0]
            callee = args[1]
            assert_call_allowed(caller, callee)
        return func(*args, **kwargs)
    return wrapper  # type: ignore[return-value]


@dataclass(frozen=True)
class LayerContract:
    """Explicit layer contract for documentation and validation."""

    layer: Layer
    may_call: tuple[Layer, ...]
    description: str


# Default layer contracts for reference
LAYER_CONTRACTS: dict[Layer, LayerContract] = {
    Layer.SUBSTRATE: LayerContract(
        layer=Layer.SUBSTRATE,
        may_call=(Layer.SUBSTRATE,),
        description="Foundation: clock, identity, errors, memory store, no outbound calls",
    ),
    Layer.GATEWAY: LayerContract(
        layer=Layer.GATEWAY,
        may_call=(Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="Adapters for external systems (LLM, shell, MCP, human)",
    ),
    Layer.PANTHEON: LayerContract(
        layer=Layer.PANTHEON,
        may_call=(Layer.PANTHEON, Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="Capability registry, selection, orchestration",
    ),
    Layer.DEMIURGE: LayerContract(
        layer=Layer.DEMIURGE,
        may_call=(Layer.DEMIURGE, Layer.PANTHEON, Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="Strategic decomposition, multi-strategy execution, synthesis",
    ),
    Layer.ARETE: LayerContract(
        layer=Layer.ARETE,
        may_call=(Layer.ARETE, Layer.DEMIURGE, Layer.PANTHEON, Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="Judgment — defines what 'better' means (non-compensatory virtue arbitration)",
    ),
    Layer.PROMETHEUS: LayerContract(
        layer=Layer.PROMETHEUS,
        may_call=(Layer.PROMETHEUS, Layer.ARETE, Layer.DEMIURGE, Layer.PANTHEON, Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="Recursive self-improvement: observe -> propose -> vet -> apply (reversible)",
    ),
    Layer.MOUTH: LayerContract(
        layer=Layer.MOUTH,
        may_call=(Layer.MOUTH, Layer.PROMETHEUS, Layer.ARETE, Layer.DEMIURGE, Layer.PANTHEON, Layer.GATEWAY, Layer.SUBSTRATE, Layer.MNEMOSYNE),
        description="The sole user interface — one identity, one point of interaction",
    ),
    Layer.MNEMOSYNE: LayerContract(
        layer=Layer.MNEMOSYNE,
        may_call=(Layer.MNEMOSYNE, Layer.SUBSTRATE),
        description="Persistent memory, provenance, ledger; callable by all",
    ),
}


def get_layer_contract(layer: Layer) -> LayerContract:
    """Get the layer contract for a given layer."""
    return LAYER_CONTRACTS.get(layer, LayerContract(layer, (), "Unknown layer"))