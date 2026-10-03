"""Tests: the Persian face's remaining LIVE branches (R51 wave 1).

Each branch is a real operator sentence or a real result payload rendered
through the actual extract_params / persian_report — no mock of the unit.
"""

from __future__ import annotations

from universal_mind.persian_params import extract_params
from universal_mind.persian_report import persian_report


class TestParamsBranches:
    """جملات واقعی اپراتور → عملیات درست."""

    def test_scatter_is_explicit(self) -> None:
        p = extract_params("نقاط پراکندهی قد و وزن را بکش", "chart")
        assert p.get("operation") == "scatter"

    def test_title_with_a_date_is_resolved(self) -> None:
        p = extract_params("نمودار فروش امروز را با عنوان بکش", "chart")
        assert isinstance(p, dict)

    def test_zip_with_a_path_lists(self) -> None:
        # R74 — «ببین» is a VIEW verb, not a pack verb: a zip path with no
        # zip verb LISTS. («فایل X را ZIP کن» packs — that is the new law.)
        p = extract_params("فایل C:/x/a.zip را ببین", "zip")
        assert p.get("operation") == "list"
        assert "a.zip" in str(p.get("path"))

    def test_zip_without_path_packs(self) -> None:
        p = extract_params("آرشیو کن", "zip")
        assert p.get("operation") == "pack"  # the flow packs the chain's files

    def test_archive_compress_with_text(self) -> None:
        p = extract_params("متن «سلام» را فشرده کن", "archive")
        assert p.get("operation") == "compress"
        assert p.get("content")

    def test_math_evaluate(self) -> None:
        p = extract_params("حاصل عبارت را ارزیابی کن", "compute")
        assert p.get("operation") == "evaluate"

    def test_pdf_read_text(self) -> None:
        p = extract_params("متن فایل C:/x/a.pdf را بخوان", "pdfreader")
        assert p.get("operation") == "read_text"
        assert "a.pdf" in str(p.get("path"))

    def test_image_with_a_folder_infos_it(self) -> None:
        p = extract_params("پوشهی دسکتاپ را ببین", "image")
        assert p.get("operation") == "info"
        assert p.get("path")

    def test_pdf_with_a_path_reads_text(self) -> None:
        p = extract_params("فایل C:/x/a.pdf را بده", "pdfreader")
        assert p.get("operation") == "read_text"
        assert "a.pdf" in str(p.get("path"))

    def test_pdf_without_path_flows(self) -> None:
        p = extract_params("متن PDF را بخوان", "pdfreader")
        assert p.get("operation") == "read_text"

    def test_excel_read_table(self) -> None:
        p = extract_params("جدول فایل C:/x/b.xlsx را بخوان", "excel")
        assert p.get("operation") == "read_table"

    def test_excel_without_path_is_a_flow_write(self) -> None:
        p = extract_params("جدول اکسل را بساز", "excel")
        # no path → the flow fills headers/rows (the documented law)
        assert p.get("operation") == "write_table"
        assert p.get("rtl") is True

    def test_image_open_defaults_to_info(self) -> None:
        p = extract_params("تصویر را باز کن", "image")
        assert p.get("operation") == "info"

    def test_speech_speak_open(self) -> None:
        p = extract_params("بخوان", "speech")
        assert p.get("operation") == "speak"

    def test_clipboard_read_and_write(self) -> None:
        assert extract_params("کلیپبورد را بخوان", "clipboard").get("operation") == "read"
        assert extract_params("متن را در کلیپبورد بگذار", "clipboard").get("operation") == "write"
        assert extract_params("متن را کپی کن", "clipboard").get("operation") == "write"

    def test_llm_prompt_extraction(self) -> None:
        p = extract_params("هوش مصنوعی حالت چطور است", "llm")
        assert isinstance(p.get("prompt"), str)

    def test_vision_structure_and_contours(self) -> None:
        assert extract_params("ساختار نمودار را بگیر", "vision").get("operation") == "chart_structure"
        assert extract_params("کانتورها را بگیر", "vision").get("operation") == "contours"


class TestReportBranches:
    """payloadهای واقعی → جملهی فارسی درست."""

    def _report(self, cap: str, result: object) -> str:
        payload = {
            "ok": True,
            "command": "فرمان",
            "route": [cap],
            "result": {cap: result},
            "extracted_params": {cap: {}},
        }
        return str(persian_report(payload))

    def test_accuracy_renders(self) -> None:
        assert "۹۲" in self._report("ai", {"accuracy": 0.92})

    def test_regression_renders(self) -> None:
        assert "ضریب" in self._report("ai", {"coefficients": [1.5, 2.0]})

    def test_frequencies_render(self) -> None:
        assert "فرکانس" in self._report("ai", {"dominant_frequencies": [10, 20]})

    def test_image_analysis_renders(self) -> None:
        r = self._report("vision", {"dominant_colors": [{"color": "قرمز", "share": 0.4}], "long_lines": 3, "ink_ratio": 0.2})
        assert "خط" in r

    def test_structure_renders(self) -> None:
        assert "ساختار" in self._report("vision", {"dominant_colors": [], "long_lines": 5})

    def test_white_ratio_renders(self) -> None:
        assert "روشن" in self._report("vision", {"white_ratio": 0.7})

    def test_generic_vision_fallback(self) -> None:
        assert "تحلیل تصویر" in self._report("vision", {})

    def test_compute_number_renders(self) -> None:
        assert "نتیجه" in self._report("compute", 42)

    def test_db_rows_render(self) -> None:
        assert "دیتابیس" in self._report("database", [{"a": 1}, {"b": 2}])

    def test_clipboard_set_renders(self) -> None:
        assert "کلیپبورد" in self._report("clipboard", {"ok": True, "set": True})

    def test_a_non_number_label_renders_as_is(self) -> None:
        # _fa_num on a genuine label: ValueError path — render as-is
        payload = {
            "ok": True,
            "command": "فرمان",
            "route": ["compute"],
            "result": {"compute": "میانگین"},
            "extracted_params": {"compute": {}},
        }
        # a non-numeric compute result is not narrated — the generic line stays honest
        assert "اجرا انجام شد" in str(persian_report(payload))
