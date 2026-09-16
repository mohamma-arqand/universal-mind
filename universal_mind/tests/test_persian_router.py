"""Tests for the Persian natural-language router (فارسی بگو، سیستم اجرا کند)."""

from __future__ import annotations

from universal_mind.persian_router import route, route_and_run


class TestRouting:
    """The deterministic Persian vocabulary maps honestly."""

    def test_single_capability_route(self) -> None:
        result = route("میانگین این اعداد را حساب کن")
        assert result.ok is True
        assert result.capabilities == ("data",)
        assert "میانگین" in result.matched_words

    def test_two_capability_chain_route(self) -> None:
        result = route("میانگین این داده‌ها را حساب کن و نمودارش کن")
        assert result.ok is True
        assert set(result.capabilities) == {"data", "chart"}
        # data runs first (it produces the input chart consumes).
        assert result.capabilities[0] == "data"

    def test_report_route_goes_to_pdf(self) -> None:
        result = route("یک گزارش پی دی اف بساز")
        assert result.ok is True
        assert "pdf" in result.capabilities

    def test_image_route(self) -> None:
        result = route("این عکس را سیاه سفید کن")
        assert result.ok is True
        assert "image" in result.capabilities

    def test_store_route_goes_to_database(self) -> None:
        result = route("این داده‌ها را ذخیره کن")
        assert result.ok is True
        assert "database" in result.capabilities

    def test_unknown_command_is_honest(self) -> None:
        result = route("فلان کار بی‌ربط")
        assert result.ok is False
        assert result.capabilities == ()
        assert result.unknown  # the honest unknown words


class TestRouteAndRun:
    """The routed chain executes real work through the unified engine."""

    def test_persian_command_runs_real_data(self) -> None:
        payload = route_and_run("میانگین این اعداد را حساب کن")
        assert payload["ok"] is True
        assert payload["route"] == ["data"]
        # The default stats series is computed for real.
        assert payload["result"]["data"]["mean"] == 5.0

    def test_persian_chain_runs_two_real_programs(self) -> None:
        payload = route_and_run("محاسبه کن و نمودارش کن")
        assert payload["ok"] is True
        assert set(payload["route"]) == {"data", "chart"}
        # Both real effects present: stats + a real PNG.
        assert payload["result"]["data"]["mean"] == 5.0
        assert payload["result"]["chart"]["bytes"] > 0

    def test_unknown_command_returns_honest_error(self) -> None:
        payload = route_and_run("پرواز کن به ماه")
        assert payload["ok"] is False
        assert payload["error"]
        assert "route" not in payload


class TestVisionAndAIRoutes:
    """«بینایی» and «یادگیری ماشین» are first-class Persian commands now."""

    def test_vision_words_route_to_vision(self) -> None:
        assert "vision" in route("تحلیل تصویر و تشخیص لبه").capabilities
        assert "vision" in route("این عکس را پردازش تصویر کن").capabilities

    def test_ai_words_route_to_ai(self) -> None:
        assert "ai" in route("یادگیری ماشین انجام بده").capabilities
        assert "ai" in route("اعداد را خوشهبندی کن").capabilities
        assert "ai" in route("مدل رگرسیون بساز").capabilities

    def test_vision_and_pdf_chain(self) -> None:
        """«تحلیل تصویر و گزارشش را بساز» -> vision → pdf (real CV + real PDF)."""
        payload = route_and_run("تحلیل تصویر این عکس و گزارشش را بساز")
        assert payload["ok"] is True
        assert "vision" in payload["route"]
        assert "pdf" in payload["route"]

    def test_cluster_command_runs_real_kmeans(self) -> None:
        """«خوشهبندی ۱ و ۲ و ۹ و ۱۰» really trains KMeans over the command's numbers."""
        payload = route_and_run("اعداد ۱ و ۲ و ۹ و ۱۰ را خوشهبندی کن")
        assert payload["ok"] is True
        centroids = payload["result"]["ai"]["centroids"]
        # Two tight groups (1,2) and (9,10): KMeans must separate them for real.
        assert len(centroids) == 2
        flat = sorted(c[0] for c in centroids)
        assert flat[0] < 5 < flat[1]

    def test_vision_runs_before_pdf(self) -> None:
        """Data-flow order: the analysis runs before the report consumes it."""
        result = route("تحلیل تصویر و گزارش پی دی اف بساز")
        assert result.capabilities.index("vision") < result.capabilities.index("pdf")


class TestOrderPriority:
    """Data-flow ordering: producers first, sinks last."""

    def test_data_before_chart_before_database(self) -> None:
        result = route("محاسبه کن، نمودار بکش، ذخیره کن")
        assert result.capabilities[0] == "data"
        assert result.capabilities[1] == "chart"
        assert result.capabilities[2] == "database"

    def test_notify_is_last(self) -> None:
        result = route("محاسبه کن و اطلاع بده")
        assert result.capabilities[-1] == "notify"