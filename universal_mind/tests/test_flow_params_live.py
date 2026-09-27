"""Tests: the flow-params LIVE branches (R49 wave 3) — the dataflow heart.

`_flow_params` is where one program's output becomes the next program's
input; every branch that builds a REAL flow is exercised here (explicit
intent always wins; only whitelisted upgrades may replace an explicit shape).
"""

from __future__ import annotations

from typing import Any

from universal_mind.orchestration import _flow_params


class TestExplicitIntentWins:
    def test_an_explicit_operation_is_never_overridden(self) -> None:
        params, flow = _flow_params(
            "chart", {"operation": "bar"}, "data", {"data": [1, 2, 3]},
            produced_paths=("p.png",)
        )
        assert params["operation"] == "bar"  # the operator named the kind
        assert flow is None

    def test_a_clipboard_read_is_never_overridden(self) -> None:
        params, flow = _flow_params(
            "clipboard", {"operation": "read"}, "chart", {"bytes": 12}
        )
        assert params["operation"] == "read"
        assert flow is None

    def test_a_pdfreader_explicit_target_wins(self) -> None:
        params, flow = _flow_params(
            "pdfreader", {"path": "doc.pdf"}, "chart", {"bytes": 5},
            produced_paths=("doc.pdf",)
        )
        assert params["path"] == "doc.pdf"
        assert flow is None


class TestChartFlows:
    def test_data_to_chart_computes_the_series(self) -> None:
        params, flow = _flow_params("chart", {}, "data", {"data": [3, 1, 2]})
        assert flow is not None
        assert params["operation"] == "line"
        assert params["series"]["محاسبهشده"] == [3.0, 1.0, 2.0]

    def test_database_rows_to_chart_bars_the_metrics(self) -> None:
        rows: list[dict[str, Any]] = [
            {"metric": "mean", "value": 5.0},
            {"metric": "median", "value": 4.0},
        ]
        params, flow = _flow_params("chart", {}, "database", rows)
        assert flow is not None
        assert params["operation"] == "bar"
        assert params["values"] == [5.0, 4.0]
        assert params["categories"] == ["mean", "median"]

    def test_bool_and_text_values_are_skipped(self) -> None:
        rows: list[dict[str, Any]] = [
            {"metric": "flag", "value": True},
            {"metric": "label", "value": "hello"},
        ]
        params, flow = _flow_params("chart", {}, "database", rows)
        assert flow is None  # nothing numeric to plot
        assert params == {}  # the params pass through honestly

    def test_a_string_number_parses(self) -> None:
        rows: list[dict[str, Any]] = [{"metric": "count", "value": "12"}]
        params, flow = _flow_params("chart", {}, "database", rows)
        assert flow is not None
        assert params["values"] == [12.0]


class TestPdfFlows:
    def test_stats_to_pdf_builds_the_rtl_table(self) -> None:
        last: dict[str, Any] = {"stats": {"count": 4, "mean": 5.5}}
        params, flow = _flow_params("pdf", {}, "data", last)
        assert flow is not None
        assert params["operation"] == "persian_report"
        assert params["stats_headers"] == ["شاخص", "مقدار"]
        assert params["stats_rows"] == [["count", "4"], ["mean", "5.5"]]

    def test_flat_numbers_fall_back_to_stats(self) -> None:
        last: dict[str, Any] = {"count": 3, "mean": 4.0, "ok": True}
        params, flow = _flow_params("pdf", {}, "data", last)
        assert flow is not None
        assert params["operation"] == "persian_report"
        assert params["stats_rows"] == [["count", "3"], ["mean", "4"]]


class TestStoreFlows:
    def test_webfetch_text_stores_named_rows(self) -> None:
        last: dict[str, Any] = {"text": "سلام دنیا این یک آزمایش است", "title": "تست"}
        params, flow = _flow_params("database", {}, "webfetch", last)
        assert flow is not None
        assert params["operation"] == "insert_many"
        assert params["table"] == "chain_results"
        assert len(params["rows"]) == 6

    def test_an_explicit_non_store_intent_is_never_overridden(self) -> None:
        last: dict[str, Any] = {"text": "سلام", "title": "تست"}
        params, flow = _flow_params("database", {"operation": "query"}, "webfetch", last)
        assert params["operation"] == "query"
        assert flow is None

    def test_an_empty_text_stores_nothing(self) -> None:
        last: dict[str, Any] = {"text": "", "title": "تست"}
        params, flow = _flow_params("database", {}, "webfetch", last)
        assert flow is None


class TestUnrelatedConsumers:
    def test_a_chart_to_speech_flow_narrates_the_artifact(self) -> None:
        """chart→speech: the toast SAYS what the chain MADE (real flow)."""
        params, flow = _flow_params(
            "speech", {"operation": "speak"}, "chart", {"bytes": 12}
        )
        assert flow is not None  # a real dataflow: the artifact summary
        assert "chart → speech" in flow


__test__ = True
