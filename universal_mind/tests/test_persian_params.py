"""Tests for Persian parameter extraction — the numbers in the sentence ARE the params."""

from __future__ import annotations

from universal_mind.persian_params import (
    extract_numbers,
    extract_numbers_between,
    extract_params,
    extract_path,
    extract_text,
)


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
        params = extract_params("یک گزارش «پیشنهاد نهایی» بساز", "pdf")
        assert params["operation"] == "document"
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
