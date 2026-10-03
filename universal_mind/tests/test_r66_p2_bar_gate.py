"""R66 P2 — a bar chart without data is a NAMED refusal (the R63-P3 law, bar edition).

The R66 sweep caught «نمودارش کن» (a bare chart request, bar kind from
the operator's stored preference) drawing [3,7,5] and reporting
«✅ اجرا انجام شد» — fabricated bars over a live green. bar() was the
one R63 gate that never got the no-data law.
"""

from __future__ import annotations

import pytest


class TestTheBarGate:
    def test_bar_without_values_refuses(self) -> None:
        from universal_mind.chart_suite import ChartSuite

        out = ChartSuite().bar(categories=None, values=None)
        assert out["ok"] is False
        assert "بدون داده" in out["error"]

    def test_bar_with_values_draws(self) -> None:
        from universal_mind.chart_suite import ChartSuite

        out = ChartSuite().bar(categories=["الف", "ب"], values=[3.0, 7.0])
        assert out["ok"] is True
        assert out["bytes"] > 0

    def test_categories_default_to_row_numbers_not_english(self) -> None:
        from universal_mind.chart_suite import ChartSuite

        out = ChartSuite().bar(categories=None, values=[1.0, 2.0, 3.0])
        assert out["ok"] is True  # Persian row labels — no x/y/z


class TestTheBareChartAskConfesses:
    def test_nemudarash_kon_confesses(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("نمودارش کن")
        assert p["ok"] is False
        assert "بدون داده" in p["agent_report"]
        assert "✅ اجرا انجام شد" not in p["agent_report"]

    def test_a_real_series_still_draws(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("نمودار میله‌ای از ۳ و ۷ و ۵ بکش")
        assert p["ok"] is True
        assert ".png" in p["agent_report"]


@pytest.mark.parametrize("kind", ["pie", "scatter", "histogram"])
def test_the_other_gates_hold(kind: str) -> None:
    """The remaining chart kinds must keep their own no-data refusals."""
    from universal_mind.chart_suite import ChartSuite

    suite = ChartSuite()
    out = suite.pie(values=None) if kind == "pie" else (
        suite.scatter(xs=None, ys=None) if kind == "scatter"
        else suite.histogram(data=None)
    )
    assert out["ok"] is False
    assert "بدون داده" in out["error"]
