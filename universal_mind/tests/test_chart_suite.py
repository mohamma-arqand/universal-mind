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
    bar = conn.connect({}, {"operation": "bar", "values": [2.0, 5.0]})
    assert bar.ok is True
    # R66 P2 — a bar without values is a NAMED refusal (no [3,7,5] default)
    bar_empty = conn.connect({}, {"operation": "bar"})
    assert bar_empty.ok is False and "بدون داده" in str(bar_empty.error)


def test_unknown_operation_fails_clean() -> None:
    conn = ChartSuiteConnector()
    result = conn.connect({}, {"operation": "hologram"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_chart_suite_joins_the_synthesis_loop() -> None:
    """The whole charting program participates in the multi-tool synthesis loop."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory
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
    # "chart" is a registered real capability in real_tool_registry — no mutation
    # of the shared table needed (the earlier mutate-then-delete pattern here was
    # a real cross-test contamination bug).
    # R63 P3: a chart in a MECHANISM test still needs REAL explicit data —
    # the silent default series is gone (honesty law), so the test feeds one.
    syn = orchestrate(
        reg, ["chart"], connector_factory=real_connector_factory,
        capability_params={"chart": {"operation": "line",
                                     "series": {"داده": [2, 3, 5, 7]}}})
    assert syn.ok is True
    assert syn.output["synthesized_from"]["chart"]["bytes"] > 0

class TestPersianChartRendering:
    """A Persian sentence deserves a Persian-rendered chart (real glyphs)."""

    def test_bar_kind_from_words(self) -> None:
        """«میلهای» names the bar operation — not the line default."""
        from universal_mind.persian_params import extract_params

        params = extract_params("نمودار میلهای فروش با ۳ و ۷ را بکش", "chart")
        assert params["operation"] == "bar"
        assert params["values"] == [3.0, 7.0]

    def test_pie_kind_from_words(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("نمودار دایرهای با ۴۰ و ۳۵ و ۲۵ بکش", "chart")
        assert params["operation"] == "pie"

    def test_line_default_unchanged(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("نمودار فروش با ۱ و ۲ و ۳", "chart")
        assert params["operation"] == "line"

    def test_persian_text_renders_real_glyphs(self) -> None:
        """Persian labels must produce substantial ink — tofu boxes would be
        sparse; real shaped glyphs carry many more dark pixels."""

        import numpy as np
        from PIL import Image

        from universal_mind.chart_suite import ChartSuite

        r = ChartSuite().bar(
            categories=["فروردین", "اردیبهشت", "خرداد"],
            values=[3, 7, 5],
            title="فروش ماهانه",
        )
        assert r["ok"] is True
        img = np.array(Image.open(r["path"]).convert("L"))
        ink = int((img < 128).sum())
        assert ink > 5000  # real shaped Persian text, not tofu boxes
