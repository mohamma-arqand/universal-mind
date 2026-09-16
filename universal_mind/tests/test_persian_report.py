"""Tests for the Persian reporter — the run's result as fluent Persian."""

from __future__ import annotations

from universal_mind.persian_report import persian_report


class TestMemoryReadback:
    """«چی ذخیره کردی؟» — the memory loop closes: store → recall → narrate."""

    def test_asking_reads_the_persistent_store(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("چی ذخیره کردی؟", "database")
        assert params["operation"] == "query"
        assert "chain_results" in params["sql"]
        assert params["persistent"] is True

    def test_storing_then_asking_round_trips(self) -> None:
        """Store real metrics, then ask — the answer contains what was stored."""
        from universal_mind.persian_router import route_and_run

        store = route_and_run("میانگین ۱ و ۵ را حساب کن و در دیتابیس ذخیره کن")
        assert store["ok"] is True
        ask = route_and_run("چی ذخیره کردی؟")
        assert ask["ok"] is True
        rows = ask["result"]["database"]
        assert isinstance(rows, list) and rows  # real rows came back
        metrics = {r["metric"] for r in rows}
        assert {"mean", "median"} <= metrics  # the computed metrics are recallable

    def test_empty_store_narrates_honestly(self) -> None:
        from universal_mind.persian_report import _render_capability

        sentence = _render_capability("database", [], None)
        assert sentence is not None
        assert "هنوز چیزی ذخیره نشده" in sentence

    def test_readback_narrates_in_fluent_persian(self) -> None:
        from universal_mind.persian_report import _render_capability

        rows = [{"metric": "mean", "value": "3"}, {"metric": "std", "value": "1.4142"}]
        sentence = _render_capability("database", rows, None)
        assert sentence is not None
        assert "میانگین=۳" in sentence
        assert "انحراف معیار=۱.۴۱۴۲" in sentence
        assert "mean" not in sentence and "std" not in sentence  # no English leak


class TestArchiveNarration:
    def test_report_narrates_the_archive(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("نمودار خطی بساز و گزارشش کن و بایگانی کن")
        report = persian_report(payload)
        assert any("→ archive" in f for f in payload["flows"])
        assert "بایگانی یکجا" in report


class TestNotifyNarration:
    def test_report_narrates_the_toast_summary(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("نمودار خطی بساز و گزارشش کن و اطلاع بده")
        report = persian_report(payload)
        assert any("→ notify" in f for f in payload["flows"])
        assert "اعلان ویندوز نشان داده شد" in report


class TestFlowNarration:
    """When data flowed (chart → pdf), the report narrates it."""

    def test_report_narrates_the_flow(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("نمودار خطی بساز و گزارشش کن")
        assert payload["flows"], "the flow must be active for chart→pdf"
        report = persian_report(payload)
        assert "🔗" in report
        assert "نمودار درونش" in report or "گزارش فارسی" in report

    def test_report_without_flow_has_no_flow_line(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۱ و ۲ را حساب کن")
        assert payload["flows"] == []
        report = persian_report(payload)
        assert "🔗" not in report


class TestRealRunsRendered:
    def test_stats_chart_store_chain(self) -> None:
        """The full stats→chart→store chain renders as fluent Persian.

        The database flow stores the COMPUTED chart metrics (named, e.g. the
        chart's contour/size figures) — the stored record is what was MADE,
        not the raw input echo."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۲ و ۴ و ۶ را حساب کن، نمودارش کن و ذخیره کن")
        report = persian_report(payload)
        assert report.startswith("✅")
        assert "میانگین ۳ عدد برابر ۴" in report          # real stats rendered
        assert "نمودار" in report and "کیلوبایت" in report  # real chart rendered
        assert "در دیتابیس ذخیره شد" in report            # real insert rendered
        assert "شاخصِ محاسبهشده" in report               # the flow: computed, named
        assert "data" not in report and "mean" not in report  # no English keys leaked

    def test_vision_command_renders_contours(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("تحلیل تصویر و تشخیص لبه")
        report = persian_report(payload)
        assert "بینایی کامپیوتر" in report
        assert ("ناحیه" in report) or ("پیکسل لبه" in report)  # a real measurement

    def test_cluster_command_renders_kmeans(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("اعداد ۱ و ۲ و ۹ و ۱۰ را خوشهبندی کن")
        report = persian_report(payload)
        assert "خوشهبندی ۲ خوشه پیدا کرد" in report  # the real KMeans result


class TestHonesty:
    def test_failed_run_renders_the_real_reason(self) -> None:
        payload = {"ok": False, "result": {}, "error": "هیچ قابلیتی شناخته نشد"}
        report = persian_report(payload)
        assert report.startswith("❌")
        assert "هیچ قابلیتی شناخته نشد" in report

    def test_per_capability_error_renders_honestly(self) -> None:
        payload = {
            "ok": False,
            "route": ["data", "chart"],
            "result": {"data": {"mean": 4.0, "count": 2}},
            "errors": {"chart": "render failed"},
        }
        report = persian_report(payload)
        assert "ناموفق" in report and "render failed" in report

    def test_never_invents_values(self) -> None:
        """A result dict with no recognizable fields renders generically, not
        with a fabricated measurement."""
        payload = {
            "ok": True,
            "route": ["compute"],
            "result": {"compute": {"mystery": 1}},
        }
        report = persian_report(payload)
        assert "میانگین" not in report  # never pretends a stats sentence


class TestNumberRendering:
    def test_persian_digits(self) -> None:
        from universal_mind.persian_report import _fa_num

        assert _fa_num(5.0) == "۵"
        assert _fa_num(12) == "۱۲"
        assert _fa_num(3.14) == "۳٫۱۴" or _fa_num(3.14) == "۳.۱۴"

    def test_kb_rendering(self) -> None:
        from universal_mind.persian_report import _kb

        assert "بایت" in _kb(500)
        assert "کیلوبایت" in _kb(2048)