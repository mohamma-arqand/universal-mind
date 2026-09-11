"""Coverage for powers/generator.py's remaining branches."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from universal_mind.powers.generator import (
    PowerGenerationError,
    _default_benchmark,
    _default_generator,
    _expected_for,
    _load_callable,
)


def test_expected_for_len_and_slug() -> None:
    assert _expected_for("len") == 3  # len((1,2,3))
    # slug normalizes "1 2 3" -> "1-2-3"
    assert _expected_for("slug") == "1-2-3"


def test_default_generator_emits_working_power() -> None:
    source, expected = _default_generator("thing", "sum the args")
    assert "def power" in source
    assert expected == 6  # sum(1,2,3)

    # slug behavior pulls in the _slug prelude
    slug_src, slug_expected = _default_generator("s", "make a slug of it")
    assert "_slug" in slug_src
    assert slug_expected == "1-2-3"


def test_load_callable_returns_callable() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.py"
        p.write_text("def power(*a, **k):\n    return 42\n", encoding="utf-8")
        fn = _load_callable(p)
        assert fn() == 42


def test_expected_for_unknown_behavior_returns_none() -> None:
    assert _expected_for("totally-unknown") is None


def test_load_callable_missing_power_raises() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.py"
        p.write_text("x = 1\n", encoding="utf-8")
        with pytest.raises(PowerGenerationError):
            _load_callable(p)


def test_benchmark_exception_scores_zero() -> None:
    def _boom(*a: object, **k: object) -> object:
        raise RuntimeError("nope")

    assert _default_benchmark(_boom, "anything") == 0.0