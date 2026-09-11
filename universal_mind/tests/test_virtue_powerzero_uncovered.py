"""Coverage for virtue.py validation branches + power_zero.py immutability."""

from __future__ import annotations

import pytest

from universal_mind.arete.virtue import (
    AreteError,
    CardinalVirtue,
    VirtueWeights,
)
from universal_mind.powers.power_zero import (
    DuplicateMintedPower,
    ImmutablePrecedence,
    PowerZero,
)


def test_negative_weight_rejected() -> None:
    with pytest.raises(AreteError):
        VirtueWeights(weights={CardinalVirtue.WISDOM: -1.0})


def test_all_zero_weights_rejected() -> None:
    with pytest.raises(AreteError):
        VirtueWeights(weights={v: 0.0 for v in CardinalVirtue})


def test_unknown_hard_gate_rejected() -> None:
    with pytest.raises(AreteError):
        # a non-cardinal string slips the type system but must be rejected at runtime
        VirtueWeights(hard_gate=frozenset({"not_a_virtue"}))  # type: ignore[arg-type]


def test_hard_gate_threshold_out_of_range_rejected() -> None:
    with pytest.raises(AreteError):
        VirtueWeights(hard_gate_threshold=1.5)
    with pytest.raises(AreteError):
        VirtueWeights(hard_gate_threshold=-0.1)


def test_accept_threshold_out_of_range_rejected() -> None:
    with pytest.raises(AreteError):
        VirtueWeights(accept_threshold=2.0)
    with pytest.raises(AreteError):
        VirtueWeights(accept_threshold=-1.0)


def test_power_zero_setattr_blocks_precedence() -> None:
    pz = PowerZero()
    attr, value = "GATE_PRECEDENCE", ("X",)
    with pytest.raises(ImmutablePrecedence):
        setattr(pz, attr, value)


def test_get_minted_powers_returns_tuple() -> None:
    PowerZero.reset_minted()
    PowerZero.mint_power("custom", "a custom power")
    minted = PowerZero.get_minted_powers()
    assert isinstance(minted, tuple)
    assert minted[0].name == "custom"
    PowerZero.reset_minted()


def test_mint_builtin_name_rejected() -> None:
    PowerZero.reset_minted()
    with pytest.raises(DuplicateMintedPower):
        PowerZero.mint_power("PowerZero", "clash")
    PowerZero.reset_minted()


def test_verify_minted_below_builtins_false() -> None:
    PowerZero.reset_minted()
    PowerZero.mint_power("below", "x")
    # Normal minting stays below built-ins (precedence starts at builtin count)
    assert PowerZero.verify_minted_below_builtins() is True

    # Force a violation by injecting a below-built-in precedence manually.
    from universal_mind.powers.power_zero import MintedPower

    PowerZero._minted_powers.append(MintedPower("bad", 0, "x", {}))
    assert PowerZero.verify_minted_below_builtins() is False
    PowerZero.reset_minted()