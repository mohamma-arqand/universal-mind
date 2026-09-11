"""Tests for real external tools — a genuine service, fail-safe."""

from __future__ import annotations

from universal_mind.io.real_tools import RealToolProvider, ToolResult, ToolService


def test_real_tool_reaches_the_service() -> None:
    service = ToolService()
    url = service.start()
    try:
        provider = RealToolProvider(url)
        result = provider.compute("sum", [1.0, 2.0, 3.0])
        assert result.ok is True
        assert result.output == 6.0
        assert result.via_fallback is False
    finally:
        service.stop()


def test_unreachable_tool_falls_back() -> None:
    # A port with nothing listening -> the provider must fall back safely.
    provider = RealToolProvider("http://127.0.0.1:1")
    result = provider.compute("sum", [1.0, 2.0])
    assert result.ok is True
    assert result.via_fallback is True
    assert result.output == "fallback"


def test_tool_result_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = ToolResult(True, 6.0, False, "real tool")
    try:
        r.ok = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_product_op_matches_arithmetic() -> None:
    service = ToolService()
    url = service.start()
    try:
        provider = RealToolProvider(url)
        result = provider.compute("product", [2.0, 3.0, 4.0])
        assert result.output == 24.0
    finally:
        service.stop()