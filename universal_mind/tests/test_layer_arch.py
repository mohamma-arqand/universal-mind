"""Tests for the completed six-layer architecture (L0..L6 + MNEMOSYNE)."""

from __future__ import annotations

from universal_mind.layers import LAYER_CONTRACTS, Layer


def test_all_seven_layers_present() -> None:
    """The charter's L0..L6 + MNEMOSYNE are all first-class layers."""
    assert Layer.SUBSTRATE.value == 0
    assert Layer.GATEWAY.value == 1
    assert Layer.PANTHEON.value == 2
    assert Layer.DEMIURGE.value == 3
    assert Layer.ARETE.value == 4
    assert Layer.PROMETHEUS.value == 5
    assert Layer.MOUTH.value == 6
    assert Layer.MNEMOSYNE.value == 7


def test_mnemosyne_is_special_perpendicular_layer() -> None:
    """MNEMOSYNE is callable by all but calls only SUBSTRATE."""
    contract = LAYER_CONTRACTS[Layer.MNEMOSYNE]
    assert contract.may_call == (Layer.MNEMOSYNE, Layer.SUBSTRATE)


def test_mouth_may_call_everything() -> None:
    """MOUTH is the top layer — it can reach every layer below it."""
    contract = LAYER_CONTRACTS[Layer.MOUTH]
    assert Layer.ARETE in contract.may_call
    assert Layer.PROMETHEUS in contract.may_call
    assert Layer.MNEMOSYNE in contract.may_call


def test_prometheus_sits_above_arete() -> None:
    """PROMETHEUS (self-improvement) depends on ARETĒ (judgment)."""
    contract = LAYER_CONTRACTS[Layer.PROMETHEUS]
    assert Layer.ARETE in contract.may_call


def test_every_layer_exists_in_contracts() -> None:
    for layer in Layer:
        assert layer in LAYER_CONTRACTS