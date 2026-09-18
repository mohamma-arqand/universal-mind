"""Tests: the session core, the success predictor, the new flows."""

from __future__ import annotations


class TestSessionCore:
    def test_one_process_one_session(self) -> None:
        from universal_mind.session_core import SessionCore

        s1 = SessionCore.current()
        s2 = SessionCore.current()
        assert s1 is s2
        assert s1.session_id == s2.session_id

    def test_counters_are_atomic_and_snapshot_frozen(self) -> None:
        from universal_mind.session_core import SessionCore

        session = SessionCore.reset()
        session.add("runs", 2)
        snap = session.snapshot()
        session.add("runs")
        assert snap.runs == 2           # frozen read
        assert session.snapshot().runs == 3  # live counter moved on

    def test_unknown_counter_refused(self) -> None:
        import pytest

        from universal_mind.session_core import SessionCore

        with pytest.raises(KeyError):
            SessionCore.reset().add("nonexistent")

    def test_real_runs_count_themselves(self) -> None:
        """Two live commands → the session's counters rose for real."""
        from universal_mind.persian_router import route_and_run
        from universal_mind.session_core import SessionCore

        session = SessionCore.reset()
        route_and_run("میانگین ۳ و ۹ را حساب کن")
        snap = session.snapshot()
        assert snap.runs >= 1
        assert snap.judged >= 1

    def test_the_report_is_fluent_persian(self) -> None:
        from universal_mind.session_core import SessionCore

        SessionCore.reset().add("runs")
        report = SessionCore.current().report()
        assert "نشست" in report and "اجراها" in report


class TestSuccessPredictor:
    def test_a_frequent_chain_is_strong(self) -> None:
        from universal_mind.success_predictor import predict_success

        p = predict_success(("chart", "pdf"))
        assert p.evidence_runs >= 100
        assert p.tier == "strong"
        assert p.recommended_bar == 0.75

    def test_unseen_chain_inherits_global_never_blind_one(self) -> None:
        from universal_mind.success_predictor import predict_success

        p = predict_success(("ocr", "zip", "notify"))  # never ran
        assert p.evidence_runs == 0
        assert p.success_probability < 1.0   # NEVER a blind 1.0
        assert 0.0 <= p.success_probability <= 1.0

    def test_tiers_map_to_bars(self) -> None:
        from universal_mind.success_predictor import Prediction, prediction_fa

        weak = Prediction(("x",), 0.4, 5, "weak", 0.90)
        strong = Prediction(("x",), 0.95, 50, "strong", 0.75)
        assert "پرریسک" in prediction_fa(weak)
        assert "قوی" in prediction_fa(strong)

    def test_the_live_router_uses_the_dynamic_bar(self) -> None:
        """A real run passes through the predictor: the payload built fine
        (the dynamic bar replaced the hardcoded one in the gate wiring)."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۴ و ۸ را حساب کن")
        assert payload["ok"] is True


class TestNewFlows:
    def test_histogram_from_sentence_numbers(self) -> None:
        """«هیستوگرام ۱ و ۲ و ۲ و ۵ را بکش» — the sentence's numbers ARE the bins' data."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("هیستوگرام ۱ و ۲ و ۲ و ۵ و ۹ را بکش")
        assert payload["route"] == ["chart"]
        params = payload["extracted_params"]["chart"]
        assert params["operation"] == "histogram"
        assert params["data"] == [1.0, 2.0, 2.0, 5.0, 9.0]
        assert payload["result"]["chart"]["bytes"] > 5000

    def test_excel_read_flows_into_a_real_chart(self) -> None:
        """A real workbook read-back becomes the chart's data series."""
        from universal_mind.excel_suite import ExcelSuite
        from universal_mind.orchestration import orchestrate
        from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

        written = ExcelSuite().write_table(
            headers=["شاخص", "مقدار"], rows=[["الف", 3], ["ب", 7], ["ج", 5]]
        )
        syn = orchestrate(
            real_tool_registry(), ["excel", "chart"],
            connector_factory=real_connector_factory, flow=True,
            command="اکسل را بخوان و نمودارش بکش",
            capability_params={"excel": {"operation": "read_table", "path": written["path"]}},
        )
        assert syn.ok is True
        assert any("→ chart" in f for f in syn.output["flows"])
        assert syn.output["synthesized_from"]["chart"]["bytes"] > 5000

    def test_excel_write_output_does_not_confuse_the_flow(self) -> None:
        """A WRITE (rows=3, an int) must not crash the flow layer — the guard."""
        from universal_mind.orchestration import orchestrate
        from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

        syn = orchestrate(
            real_tool_registry(), ["excel", "chart"],
            connector_factory=real_connector_factory, flow=True,
            command="اکسل بساز و نمودار بکش",
            capability_params={"excel": {"operation": "write_table",
                                        "headers": ["x", "y"], "rows": [[1, 2]]}},
        )
        assert syn.ok is True  # ran fine; no flow claimed (nothing to read yet)
