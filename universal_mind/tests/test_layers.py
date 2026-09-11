"""Tests for the layer rule enforcement (assert_call_allowed + @layered)."""

from __future__ import annotations

import pytest

from universal_mind.layers import (
    Layer,
    LayerViolation,
    assert_call_allowed,
    get_layer_contract,
    layered,
)


class _LayerObj:
    LAYER: Layer

    def __init__(self, layer: Layer) -> None:
        self.LAYER = layer


def test_same_layer_is_allowed() -> None:
    assert_call_allowed(_LayerObj(Layer.DEMIURGE), _LayerObj(Layer.DEMIURGE))  # no raise


def test_layer_minus_one_is_allowed() -> None:
    assert_call_allowed(_LayerObj(Layer.DEMIURGE), _LayerObj(Layer.PANTHEON))  # no raise


def test_mnemosyne_callable_by_any_layer() -> None:
    assert_call_allowed(_LayerObj(Layer.MOUTH), _LayerObj(Layer.MNEMOSYNE))  # no raise


def test_upward_call_is_violation() -> None:
    with pytest.raises(LayerViolation):
        assert_call_allowed(_LayerObj(Layer.PANTHEON), _LayerObj(Layer.DEMIURGE))


def test_missing_layer_raises() -> None:
    with pytest.raises(LayerViolation):
        assert_call_allowed(object(), object())


def test_layer_violation_message_names_layers() -> None:
    with pytest.raises(LayerViolation) as exc:
        assert_call_allowed(_LayerObj(Layer.PANTHEON), _LayerObj(Layer.DEMIURGE))
    msg = str(exc.value)
    assert "PANTHEON" in msg and "DEMIURGE" in msg


def test_layered_decorator_enforces() -> None:
    @layered
    def cross_call(caller: object, callee: object) -> str:
        return "ok"

    assert cross_call(_LayerObj(Layer.DEMIURGE), _LayerObj(Layer.PANTHEON)) == "ok"
    with pytest.raises(LayerViolation):
        cross_call(_LayerObj(Layer.PANTHEON), _LayerObj(Layer.DEMIURGE))


def test_get_layer_contract_known_and_unknown() -> None:
    contract = get_layer_contract(Layer.ARETE)
    assert contract.layer is Layer.ARETE
    assert Layer.MNEMOSYNE in contract.may_call


def test_layer_enum_values_match_charter() -> None:
    assert Layer.SUBSTRATE.value == 0
    assert Layer.MOUTH.value == 6
    assert Layer.MNEMOSYNE.value == 7