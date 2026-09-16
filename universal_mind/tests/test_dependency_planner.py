"""Tests: the dependency planner — topology + synthesis-aware operation choice."""

from __future__ import annotations

from universal_mind.dependency_planner import plan_chain, plan_params


class TestTopology:
    def test_consumer_after_producer_even_when_said_backwards(self) -> None:
        """«گزارش بساز و نمودارش کن» — pdf was said FIRST, but it needs the
        chart, so the plan runs chart first. The words are the WHAT; the
        operations' needs decide the WHEN."""
        plan = plan_chain(["pdf", "chart"])
        caps = [s.capability for s in plan.steps]
        assert caps == ["chart", "pdf"]
        assert plan.reorder_happened is True
        assert any("تولیدکننده" in n for n in plan.notes)

    def test_already_correct_order_untouched(self) -> None:
        plan = plan_chain(["chart", "pdf"])
        assert [s.capability for s in plan.steps] == ["chart", "pdf"]
        assert plan.reorder_happened is False

    def test_producer_only_chain_untouched(self) -> None:
        plan = plan_chain(["data", "chart"])
        assert [s.capability for s in plan.steps] == ["data", "chart"]
        assert plan.reorder_happened is False

    def test_two_dependent_consumers_both_after_the_producer(self) -> None:
        """chart feeds pdf (image) and data feeds chart (series): the plan
        must place every dependent after its dependency. database has no
        dependency, so its slot is free (only its relative order to its OWN
        dependencies is guaranteed)."""
        plan = plan_chain(["pdf", "database", "chart", "data"])
        caps = [s.capability for s in plan.steps]
        assert caps.index("chart") < caps.index("pdf")   # image dependency
        assert caps.index("data") < caps.index("chart")  # series dependency
        # and nothing was dropped
        assert sorted(caps) == ["chart", "data", "database", "pdf"]


class TestOperationSelection:
    def test_pdf_gets_persian_report_when_chain_has_an_image_producer(self) -> None:
        """No explicit pdf operation in the sentence → the planner picks the
        operation that EMBEDS the chart (real synthesis), and says why."""
        plan = plan_chain(["chart", "pdf"])
        pdf_step = [s for s in plan.steps if s.capability == "pdf"][0]
        assert pdf_step.operation == "persian_report"
        assert "سنتز" in pdf_step.reason

    def test_explicit_operation_is_never_overridden(self) -> None:
        """The operator said invoice — the planner keeps invoice, no inference."""
        plan = plan_chain(
            ["chart", "pdf"],
            {"pdf": {"operation": "invoice", "title": "قبض"}},
        )
        pdf_step = [s for s in plan.steps if s.capability == "pdf"][0]
        assert pdf_step.operation == "invoice"
        assert "صریح" in pdf_step.reason

    def test_params_materialized_for_orchestrator(self) -> None:
        plan = plan_chain(["chart", "pdf"])
        params = plan_params(plan)
        assert params["pdf"]["operation"] == "persian_report"
        # chart keeps its suite default (no forced operation)
        assert "chart" not in params or "operation" not in params["chart"]

    def test_producer_only_no_needs_based_choice(self) -> None:
        plan = plan_chain(["data", "database"])
        for step in plan.steps:
            assert step.operation is None  # defaults, honestly


class TestStatsFlowTopology:
    def test_pdf_waits_for_data_even_when_said_first(self) -> None:
        """«گزارش بساز و میانگینها را حساب کن» — pdf needs the stats table."""
        plan = plan_chain(["pdf", "data"])
        caps = [s.capability for s in plan.steps]
        assert caps == ["data", "pdf"]
        assert plan.reorder_happened is True

    def test_full_chain_orders_all_dependencies(self) -> None:
        """data → chart → pdf: every consumer waits for every producer."""
        plan = plan_chain(["pdf", "chart", "data"])
        caps = [s.capability for s in plan.steps]
        assert caps == ["data", "chart", "pdf"]


class TestPlanHonesty:
    def test_never_invents_or_drops_capabilities(self) -> None:
        caps = ["pdf", "chart", "data"]
        plan = plan_chain(caps)
        assert sorted(s.capability for s in plan.steps) == sorted(caps)

    def test_empty_chain_is_an_empty_plan(self) -> None:
        plan = plan_chain([])
        assert plan.steps == ()
        assert plan_params(plan) == {}
