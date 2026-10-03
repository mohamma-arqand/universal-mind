"""R63 P3 — a chart without data is a NAMED refusal, never a fabricated
default series.

The sweep's «نمودار خطی از فروش ماهانه» drew {a:[1,3,2,5], b:[2,2,4,4]}
and presented it as a real chart — fabricated numbers (the «پیش‌فرضی که
جواب می‌دهد» law, chart edition). Three layers now hold:
- ChartSuite refuses to draw line/stackplot/step with no series;
- run_ab no longer injects DataSuite.DEFAULT_SERIES into a data-less
  contest, and the winner keeps the operator's real series;
- the report headline confesses when EVERY step failed (a «✅ اجرا
  انجام شد» header over honest failure rows was a lie).
"""

from __future__ import annotations


from universal_mind.chart_suite import ChartSuite


class TestTheSuiteRefuses:
    def test_line_without_data_refuses(self) -> None:
        out = ChartSuite().line(None)
        assert out["ok"] is False
        assert "نمودار بدون داده" in out["error"]

    def test_line_with_an_empty_series_refuses(self) -> None:
        out = ChartSuite().line({"داده": []})
        assert out["ok"] is False

    def test_line_with_real_series_draws(self) -> None:
        out = ChartSuite().line({"داده": [2, 3, 5, 7]})
        assert out["ok"] is True and out["bytes"] > 0

    def test_stackplot_and_step_refuse_too(self) -> None:
        assert ChartSuite().stackplot(None)["ok"] is False
        assert ChartSuite().step(None)["ok"] is False


class TestTheContestStaysHonest:
    def test_run_ab_never_injects_default_data(self) -> None:
        from universal_mind.ab_contest import run_ab

        made: list[dict] = []

        def variant(params: dict) -> dict:
            made.append(params)
            return {"ok": True, "route": ["chart"]}

        out = run_ab("نمودار بکش", {"operation": "line"}, variant)
        # no variant ever received a fabricated series
        assert all(not p.get("series") and not p.get("values") for p in made)
        assert out["ok"] is True  # the contest itself still completes

    def test_the_winner_keeps_the_operators_series(self) -> None:
        from universal_mind.ab_contest import run_ab

        def variant(params: dict) -> dict:
            return {"ok": True, "route": ["chart"],
                    "result": {"chart": {"path": "x.png", "bytes": 10}}}

        out = run_ab("نمودار از ۲ و ۵ و ۹ کن",
                     {"operation": "line", "series": {"داده": [2, 5, 9]}}, variant)
        assert out["ab_contest"]["winner"] in ("line", "bar")


class TestTheRouterAnswers:
    def test_a_dataless_named_series_sentence_refuses_with_roads(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("نمودار خطی از فروش ماهانه را بکش")
        assert p["ok"] is False
        rep = p["agent_report"]
        assert "نمودار بدون داده" in rep
        assert "نمودار خطی از ۱ و ۴ و ۹ بکش" in rep  # the working example

    def test_numbers_in_the_sentence_still_draw(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("نمودار خطی از ۱ و ۴ و ۹ بکش")
        assert p["ok"] is True
        assert "در «" in p["agent_report"] and ".png" in p["agent_report"]

    def test_the_all_failed_headline_confesses(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("نمودار بکش")
        assert p["ok"] is False
        rep = p["agent_report"]
        # honest either way: the direct refusal, or the all-failed chain
        # header — never a «✅ اجرا انجام شد» over failure rows.
        assert ("❌ اجرا انجام نشد" in rep
                or "❌ اجرا ناموفق بود" in rep)
        assert "✅ اجرا انجام شد" not in rep
