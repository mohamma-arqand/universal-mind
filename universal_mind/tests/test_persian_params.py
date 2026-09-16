"""Tests for Persian parameter extraction — the numbers in the sentence ARE the params."""

from __future__ import annotations

from universal_mind.persian_params import (
    extract_numbers,
    extract_numbers_between,
    extract_params,
    extract_path,
    extract_text,
)


class TestStoreIsRealInsert:
    def test_store_command_produces_insert_many(self) -> None:
        """«ذخیره کن» + numbers -> a real insert_many, NOT an empty query."""
        params = extract_params("میانگین ۱۰ و ۲۰ و ۳۰ را ذخیره کن", "database")
        assert params["operation"] == "insert_many"
        assert params["rows"] == [{"value": "10.0"}, {"value": "20.0"}, {"value": "30.0"}]

    def test_query_without_store_stays_query(self) -> None:
        """Without «ذخیره», database stays a read-only query (never an insert)."""
        params = extract_params("از دیتابیس کوئری بگیر", "database")
        assert params["operation"] == "query"

    def test_store_route_and_run_inserts_for_real(self) -> None:
        """End-to-end: the Persian store command really inserts into SQLite.

        The database flow upgrades a raw-number echo into the COMPUTED results:
        the six real metrics (mean/std/min/max/median/count), named by metric —
        storing what was computed beats re-stating the input."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۱۰ و ۲۰ و ۳۰ را حساب کن و در دیتابیس ذخیره کن")
        assert payload["ok"] is True
        assert payload["result"]["database"]["inserted"] == 6  # the computed metrics
        assert any("→ database" in f for f in payload["flows"])  # the flow, narrated


class TestColloquialAndFolders:
    def test_colloquial_forms_route_the_same(self) -> None:
        """محاوره («میانگینشو»، «نمودارشو») routes exactly like formal Persian."""
        from universal_mind.persian_router import route

        assert route("میانگینشو حساب کن").capabilities == ("data",)
        assert route("نمودارشو بکش").capabilities == ("chart",)
        assert route("ذخیرهش کن").capabilities == ("database",)

    def test_resolve_folder_maps_desktop_for_real(self) -> None:
        """«از دسکتاپ» resolves to the REAL Windows Desktop folder on this machine."""
        import os
        from pathlib import Path

        from universal_mind.persian_params import resolve_folder

        result = resolve_folder("این عکس را از دسکتاپ سیاه سفید کن")
        if os.environ.get("USERPROFILE") and (Path(os.environ["USERPROFILE"]) / "Desktop").exists():
            assert result is not None
            assert "Desktop" in result
        else:
            assert result is None  # honest: no profile / no folder

    def test_image_params_get_real_folder(self) -> None:
        """extract_params for image with «از دسکتاپ» carries the real folder path."""
        import os
        from pathlib import Path

        params = extract_params("این عکس را از دسکتاپ سیاه سفید کن", "image")
        profile = os.environ.get("USERPROFILE")
        if profile and (Path(profile) / "Desktop").exists():
            assert params.get("folder") and "Desktop" in params["folder"]
        else:
            assert "folder" not in params  # honest absence


class TestNumbers:
    def test_persian_digits_extracted(self) -> None:
        assert extract_numbers("میانگین ۲ و ۴ و ۶ را حساب کن") == [2.0, 4.0, 6.0]

    def test_arabic_digits_extracted(self) -> None:
        assert extract_numbers("محاسبه ٣ و ٥") == [3.0, 5.0]

    def test_western_digits_and_decimals(self) -> None:
        assert extract_numbers("میانگین 2.5 و 3") == [2.5, 3.0]

    def test_mixed_digits(self) -> None:
        assert extract_numbers("۲ و 3 و ۴.۵") == [2.0, 3.0, 4.5]

    def test_no_numbers_is_empty(self) -> None:
        assert extract_numbers("سلام دنیا") == []

    def test_numbers_between_chains_only_chained(self) -> None:
        # «۲ و ۴ و ۶» is a chain (number و number); «صفحه ۲ و داده ۷» has a word
        # between the numbers, so it is NOT a number chain (the regex only joins
        # digit و digit) — the honest extraction is empty here.
        assert extract_numbers_between("میانگین ۲ و ۴ و ۶") == [2.0, 4.0, 6.0]
        assert extract_numbers_between("صفحه ۲ و داده ۷") == []


class TestText:
    def test_persian_guillemets(self) -> None:
        assert extract_text("یک گزارش با عنوان «گزارش فروش» بساز") == "گزارش فروش"

    def test_double_quotes(self) -> None:
        assert extract_text('یک سند "سالانه" بساز') == "سالانه"

    def test_ba_matn(self) -> None:
        assert extract_text("اطلاع بده با متن کار تمام شد") == "کار تمام شد"

    def test_no_text_returns_none(self) -> None:
        assert extract_text("میانگین ۲ و ۳") is None


class TestPath:
    def test_windows_path(self) -> None:
        assert extract_path("اطلاعات فایل C:/data/test.csv را بخوان") == "C:/data/test.csv"

    def test_no_path_returns_none(self) -> None:
        assert extract_path("میانگین ۲ و ۳") is None


class TestExtractParams:
    """The bridge: what the operator SAID becomes what the suite NEEDS."""

    def test_data_stats_with_real_numbers(self) -> None:
        params = extract_params("میانگین ۲ و ۴ و ۶ را حساب کن", "data")
        assert params["operation"] == "stats"
        assert params["data"] == [2.0, 4.0, 6.0]

    def test_chart_with_series_and_title(self) -> None:
        params = extract_params("نمودار خطی «فروش فصلی» از ۵ و ۱۰", "chart")
        assert params["operation"] == "line"
        assert params["series"]["داده"] == [5.0, 10.0]
        assert params["title"] == "فروش فصلی"

    def test_pdf_with_title(self) -> None:
        """A Persian command now produces a Persian RTL document (not Latin-only)."""
        params = extract_params("یک گزارش «پیشنهاد نهایی» بساز", "pdf")
        assert params["operation"] == "persian_rtl"
        assert params["title"] == "پیشنهاد نهایی"

    def test_compute_builds_a_real_expression(self) -> None:
        params = extract_params("جمع ۲ و ۳ و ۴", "compute")
        assert params["operation"] == "evaluate"
        assert params["expression"] == "2.0 + 3.0 + 4.0"

    def test_notify_uses_command_as_body(self) -> None:
        params = extract_params("اطلاع بده با متن کار تمام شد", "notify")
        assert params["operation"] == "notify"
        assert params["body"] == "اطلاع بده با متن کار تمام شد"

    def test_data_without_numbers_falls_back_to_default(self) -> None:
        params = extract_params("آمار کلی", "data")
        assert params["operation"] == "stats"
        assert "data" not in params  # the suite's default series applies

    def test_unknown_capability_gets_empty(self) -> None:
        assert extract_params("هرچی", "nonexistent") == {}
