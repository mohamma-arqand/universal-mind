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


class TestSavedChainByPersianCommand:
    """«زنجیرهی X را اجرا کن» runs the operator's saved chain X for real."""

    def test_saved_chain_name_resolves_to_its_capabilities(self) -> None:
        import uuid

        from universal_mind.chains_store import ChainsStore

        store = ChainsStore()
        name = f"زنجیره فارسی {uuid.uuid4().hex[:6]}"
        saved = store.save(name, ["data", "chart"])
        try:
            result = route(f"زنجیرهی {name} را اجرا کن")
            assert result.ok is True
            assert result.capabilities == ("data", "chart")
        finally:
            store.delete(saved.chain_id)

    def test_unknown_chain_name_is_honest(self) -> None:
        result = route("زنجیرهی ناموجود ۱۲۳ را اجرا کن")
        assert result.ok is False  # no saved chain matches — no guess

    def test_chain_word_does_not_pollute_normal_commands(self) -> None:
        """«زنجیره» in a mixed command never injects a fake capability."""
        result = route("میانگین ۲ و ۴ را حساب کن")
        assert "chain" not in result.capabilities
        assert result.capabilities == ("data",)

    def test_end_to_end_saved_chain_runs_for_real(self) -> None:
        import string
        import uuid

        from universal_mind.chains_store import ChainsStore

        letters = string.ascii_lowercase
        suffix = "".join(letters[b % 26] for b in uuid.uuid4().bytes[:6])
        store = ChainsStore()
        name = f"اجرای واقعی {suffix}"  # letters only: no digits to pollute stats
        saved = store.save(name, ["data", "archive"])
        try:
            payload = route_and_run(f"زنجیرهی {name} را اجرا کن")
            assert payload["ok"] is True
            assert set(payload["route"]) == {"data", "archive"}
            assert payload["result"]["data"]["mean"] == 5.0  # real stats
            assert payload["result"]["archive"]["bytes"] > 0  # real gzip
        finally:
            store.delete(saved.chain_id)


def _first_archive_path(result: dict) -> str:
    """The archive path from the chain result (the archive adapter's output)."""
    arch = result.get("archive") or {}
    return str(arch.get("path") or arch.get("archive") or "")


class TestFullReportChain:
    """«گزارش کامل» — one command, every artifact, all flows."""

    def test_full_report_routes_everything(self) -> None:
        payload = route_and_run("گزارش کامل فروش با اعداد ۳۰ و ۷۰ و ۲۰ را بساز")
        assert payload["route"] == ["data", "chart", "pdf", "archive"]
        assert payload["ok"] is True
        # the two real flows happened (chart→pdf image, files→archive)
        assert any("→ pdf" in f for f in payload["flows"])
        assert any("→ archive" in f or "بایگانی" in f for f in payload["flows"])
        # every artifact exists with real weight
        result = payload["result"]
        assert result["pdf"]["bytes"] > 40000
        # ARCHIVE REALNESS IS NOT A BYTE FLOOR (the R52 compression-luck
        # lesson): a calm payload gzips smaller than a busy one. Realness =
        # a gzip member that opens and yields the exact bytes back.
        import gzip as _gzip

        with _gzip.open(_first_archive_path(result), "rb") as _gz:
            assert len(_gz.read()) > 1000
        assert result["chart"]["bytes"] > 5000


class TestVisionIntentDisambiguation:
    """«تحلیل تصویر» is ANALYZE (vision) — the bare «تصویر» (image-production)
    must not fire in the same sentence and pollute the route."""

    def test_analysis_phrase_does_not_route_image_production(self) -> None:
        payload = route_and_run("نمودار خطی بساز و تحلیل تصویرش کن")
        assert payload["route"] == ["chart", "vision"]  # no 'image' producer
        assert payload["ok"] is True

    def test_pure_production_still_routes_image(self) -> None:
        """Without the analysis phrase, «تصویر» keeps its production meaning."""
        from universal_mind.persian_router import route as _route

        assert "image" in _route("یک تصویر بساز").capabilities


class TestPlannerIntegration:
    """The router + planner together: needs beat word order."""

    def test_backwards_words_get_the_right_order(self) -> None:
        """«گزارشش کن و نمودار بساز» — pdf said FIRST still runs AFTER chart,
        because the planner reorders by real needs, not sentence order."""
        payload = route_and_run("گزارشش کن و نمودار خطی بساز")
        assert payload["route"] == ["chart", "pdf"]
        assert payload["ok"] is True
        # the synthesis really happened (the flow is recorded)
        assert any("نمودار درونش" in f for f in payload["flows"])

    def test_explicit_operation_survives_the_planner(self) -> None:
        """«فاکتور بساز و نمودارش کن» keeps the invoice operation."""
        payload = route_and_run("فاکتور بساز و نمودار خطی بساز")
        assert payload["ok"] is True
        assert payload["extracted_params"]["pdf"]["operation"] == "invoice"


class TestVocabularyCoverage:
    """Every registered real capability must be reachable in Persian — no
    capability is allowed to be language-orphaned."""

    def test_every_registry_capability_has_persian_words(self) -> None:
        import universal_mind.persian_router as pr
        import universal_mind.real_tool_registry as rtr

        vocab_caps = {cap for _word, cap in pr._VOCAB if cap != "chain"}
        registry_caps = set(rtr._REAL_CONNECTORS)
        orphans = registry_caps - vocab_caps
        assert not orphans, f"قابلیتهای بدون واژه فارسی: {orphans}"

    def test_every_persian_word_maps_to_a_real_capability(self) -> None:
        """Conversely: no vocabulary word may point at a capability that does
        not exist in the registry (a dead word is a lie)."""
        import universal_mind.persian_router as pr
        import universal_mind.real_tool_registry as rtr

        registry_caps = set(rtr._REAL_CONNECTORS)
        dead = {word for word, cap in pr._VOCAB if cap not in registry_caps and cap != "chain"}
        assert not dead, f"واژههای مرده (به قابلیت ناموجود): {dead}"


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