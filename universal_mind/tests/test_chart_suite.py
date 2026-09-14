"""Tests for the integrated ChartSuite (full matplotlib capability surface)."""

from __future__ import annotations

from pathlib import Path

from universal_mind.chart_suite import ChartSuite, ChartSuiteConnector


def test_line_chart_produces_a_real_png() -> None:
    suite = ChartSuite()
    out = suite.line({"temp": [10, 14, 12, 18], "load": [5, 6, 6, 9]}, title="Server telemetry")
    assert out["ok"] is True
    p = Path(out["path"])
    assert p.exists() and out["bytes"] > 0
    # A real PNG starts with the PNG magic bytes.
    assert p.read_bytes()[:4] == b"\x89PNG"


def test_bar_chart_produces_a_real_png() -> None:
    suite = ChartSuite()
    out = suite.bar(["web", "db", "cache"], [30, 50, 20])
    assert out["ok"] is True and out["bytes"] > 0


def test_pie_histogram_scatter_all_real() -> None:
    suite = ChartSuite()
    assert suite.pie([50, 30, 20], ["win", "mac", "linux"])["ok"] is True
    assert suite.histogram([1, 1, 2, 3, 3, 3, 5, 8])["ok"] is True
    assert suite.scatter([1, 2, 3], [4, 1, 7])["ok"] is True


def test_connector_dispatches_operations() -> None:
    conn = ChartSuiteConnector()
    line = conn.connect({}, {"operation": "line", "series": {"s": [1, 2, 3]}})
    assert line.ok is True and line.output["bytes"] > 0
    bar = conn.connect({}, {"operation": "bar"})
    assert bar.ok is True


def test_unknown_operation_fails_clean() -> None:
    conn = ChartSuiteConnector()
    result = conn.connect({}, {"operation": "hologram"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_chart_suite_joins_the_synthesis_loop() -> None:
    """The whole charting program participates in the multi-tool synthesis loop."""
    import universal_mind.real_tool_registry as rtr
    from universal_mind.orchestration import orchestrate
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(name="chart", capability="chart",
                           connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                           absorbable=True))
    rtr._REAL_CONNECTORS["chart"] = ChartSuiteConnector  # one-line registration
    try:
        syn = orchestrate(reg, ["chart"], connector_factory=rtr.real_connector_factory)
        assert syn.ok is True
        assert syn.output["synthesized_from"]["chart"]["bytes"] > 0
    finally:
        del rtr._REAL_CONNECTORS["chart"]