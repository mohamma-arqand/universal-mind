"""Tests that Power Zero generates *substantive* powers, not stubs."""

from __future__ import annotations

from universal_mind.powers.generator import GeneratedPower, PowerZeroGenerator
from universal_mind.powers.power_zero import PowerZero


def _generate(name: str, description: str) -> GeneratedPower:
    PowerZero.reset_minted()
    return PowerZeroGenerator().generate(name, description)


def test_sum_power_embeds_real_computation() -> None:
    """A 'sum' power embeds a real computation, not a stub."""
    result = _generate("adder", "compute the sum of arguments")
    assert result.accepted
    assert result.callable is not None
    assert "return sum(args)" in result.source
    # The canonical probe is (1, 2, 3) -> sum is 6.
    assert result.callable(1, 2, 3, x=1, y=2) == 6


def test_join_power_joins_arguments() -> None:
    result = _generate("joiner", "join arguments together")
    assert result.accepted
    assert result.callable is not None
    assert result.callable(1, 2, 3, x=1, y=2) == "1 2 3"


def test_upper_power_transforms() -> None:
    result = _generate("upperer", "make the text upper case")
    assert result.accepted
    assert result.callable is not None
    assert result.callable(1, 2, 3, x=1, y=2) == "1 2 3"


def test_count_power_counts_keyword_arguments() -> None:
    result = _generate("counter", "count the keyword arguments")
    assert result.accepted
    assert result.callable is not None
    # 'count' behaviour returns len(kwargs) over the canonical probe.
    assert result.callable(1, 2, 3, x=1, y=2) == 2


def test_source_is_not_a_tag_echo() -> None:
    """The generated source is substantive, not just an echo stub."""
    result = _generate("summer", "compute the sum")
    assert "return sum(args)" in result.source
    assert "return 'minted:" not in result.source


def test_generator_is_deterministic() -> None:
    PowerZero.reset_minted()
    a = PowerZeroGenerator().generate("join-x", "join arguments")
    PowerZero.reset_minted()
    b = PowerZeroGenerator().generate("join-x", "join arguments")
    assert a.source == b.source
    assert a.benchmark_score == b.benchmark_score