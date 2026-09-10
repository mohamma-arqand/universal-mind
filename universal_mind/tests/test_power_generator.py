"""Tests for the executable Power Zero — generate → sandbox → benchmark → arbitrate."""

from __future__ import annotations

from universal_mind.powers.generator import PowerZeroGenerator
from universal_mind.powers.power_zero import PowerZero


def _gen() -> PowerZeroGenerator:
    return PowerZeroGenerator()


def _reset() -> None:
    PowerZero.reset_minted()


def test_generator_accepts_a_working_power() -> None:
    """A power that reproduces its expected output clears the gate and is minted."""
    _reset()
    gen = _gen()
    result = gen.generate("echo-tag", "echoes a canonical tag")
    assert result.accepted is True
    assert result.minted is not None
    assert result.minted.precedence >= 7  # strictly below all 7 built-ins
    assert result.callable is not None
    assert result.callable() == "minted:echo-tag"


def test_minted_power_never_outranks_builtin() -> None:
    _reset()
    gen = _gen()
    gen.generate("p1", "a")
    gen.generate("p2", "b")
    assert PowerZero.verify_minted_below_builtins() is True
    names = PowerZero.get_precedence()
    # The built-in 7 stay first; minted powers append in order.
    assert names[:7] == PowerZero.get_builtin_precedence()
    assert "p1" in names and "p2" in names
    assert names.index("p1") < names.index("p2")


def test_rejected_power_is_not_minted() -> None:
    """A power that fails justice arbitration is rejected and never minted."""
    _reset()
    # A generator whose power emits something but the benchmark always fails
    # (wisdom low) — the arbitration refuses it.
    gen = PowerZeroGenerator(
        benchmark=lambda fn, expected: 0.0,
    )
    result = gen.generate("bad", "this will fail")
    assert result.accepted is False
    assert result.minted is None
    assert "bad" not in PowerZero.get_precedence()


def test_generated_source_never_lands_in_tree() -> None:
    """The generated source is writable only inside a throwaway sandbox."""
    _reset()
    gen = _gen()
    result = gen.generate("s", "s")
    from pathlib import Path

    # The sandbox dir is gone; the source exists only as the returned string.
    assert result.source.startswith("# Generated power 's'")
    # Nothing titled 's.py' exists in the source tree's powers dir.
    tree_here = Path(__file__).parent.parent / "powers" / "s.py"
    assert not tree_here.exists()


def test_deterministic_generation() -> None:
    _reset()
    a = _gen().generate("x", "x")
    _reset()  # reset so 'x' isn't a duplicate
    b = _gen().generate("x", "x")
    assert a.source == b.source
    assert a.benchmark_score == b.benchmark_score
    assert a.accepted == b.accepted


def test_duplicate_mint_raises_on_second_generation() -> None:
    """A second mint of the same name is refused by PowerZero itself."""
    _reset()
    gen = _gen()
    gen.generate("dup", "first")
    import pytest

    from universal_mind.powers.power_zero import DuplicateMintedPower

    with pytest.raises(DuplicateMintedPower):
        gen.generate("dup", "second")