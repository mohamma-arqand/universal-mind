"""Tests: the compound-command fixes — verb-stripped titles, spoken counts."""

from __future__ import annotations


class TestCompoundCommands:
    def test_title_never_contains_the_command_verb(self) -> None:
        """«با عنوان فروش فصل بساز» → the title is «فروش فصل», never «...بساز»."""
        from universal_mind.persian_params import extract_text

        assert extract_text("نمودار خطی با عنوان فروش فصل بساز") == "فروش فصل"
        assert extract_text("گزارش را به نام پایان فصل بساز") == "پایان فصل"

    def test_title_without_verb_stays_whole(self) -> None:
        from universal_mind.persian_params import extract_text

        assert extract_text("با عنوان موجودی انبار") == "موجودی انبار"

    def test_spoken_count_is_real_data(self) -> None:
        """«جدول با سه سطر ذخیره کن» — the Persian word «سه» becomes 3 rows."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("جدول با سه سطر ذخیره کن")
        params = payload["extracted_params"]["database"]
        assert params["operation"] == "insert_many"
        assert len(params["rows"]) == 3

    def test_hist_title_holds_all_numbers(self) -> None:
        """«هیستوگرام با عنوان توزیع از ۱ و ۲ و ۳ بساز» — data intact."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("هیستوگرام با عنوان توزیع از ۱ و ۲ و ۳ بساز")
        params = payload["extracted_params"]["chart"]
        assert params["operation"] == "histogram"
        assert params["data"] == [1.0, 2.0, 3.0]
        assert "بساز" not in params.get("title", "")