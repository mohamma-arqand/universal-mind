"""Tests for the real node-backed compute tool (third real effect)."""

from __future__ import annotations

from universal_mind.compute_adapter import ComputeToolConnector
from universal_mind.real_compute import ComputeTool


def test_evaluate_returns_real_json_value() -> None:
    conn = ComputeToolConnector()
    result = conn.connect({}, {"operation": "evaluate", "expression": "2 + 2"})
    assert result.ok is True
    assert result.output == 4


def test_evaluate_complex_expression() -> None:
    conn = ComputeToolConnector()
    result = conn.connect({}, {"operation": "evaluate", "expression": "Math.max(3, 9, 5)"})
    assert result.ok is True
    assert result.output == 9


def test_unknown_operation_fails_clean() -> None:
    conn = ComputeToolConnector()
    result = conn.connect({}, {"operation": "nonsense"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_empty_expression_fails_clean() -> None:
    tool = ComputeTool()
    result = tool.evaluate(expression="   ")
    assert result["ok"] is False
    assert "empty expression" in result["error"]


def test_invalid_expression_reports_error() -> None:
    tool = ComputeTool()
    result = tool.evaluate(expression="this is not js")
    assert result["ok"] is False