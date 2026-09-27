"""Tests: the LIVE branches of the Persian reporter (R49 wave 2).

Every branch of `_render_capability` that narrates a REAL run is exercised —
the goal report (agent_loop's step verdicts), the speech outcome (real voice +
the blocked-env remedy), the excel read-back, and the single-miss branches
(screenshot/webfetch/pdfreader/ocr). A report sentence no test passes over is
an unverified promise to the operator.
"""

from __future__ import annotations

from typing import Any

from universal_mind.persian_report import _render_capability, persian_report


class TestGoalReportNarration:
    """The agent_loop run report — step verdicts narrated as one goal."""

    def test_a_finished_goal_narrates_its_verdicts(self) -> None:
        result: dict[str, Any] = {
            "report": "گام ۱: ✅ میانگین ۴ شد\nگام ۲: ✅ گزارش ساخته شد",
            "steps": 2,
            "finished": True,
        }
        sentence = _render_capability("goal", result, None)
        assert sentence is not None
        assert sentence.startswith("🎯 هدف —")
        assert "۲ گام داوری شد" in sentence
        assert "گام ۱" in sentence

    def test_an_unfinished_goal_says_so(self) -> None:
        result: dict[str, Any] = {
            "report": "گام ۱: ✅ انجام شد\nگام ۲: ❌ شکست",
            "steps": 1,
            "finished": False,
        }
        sentence = _render_capability("goal", result, None)
        assert sentence is not None
        assert "ناتمام" in sentence
        assert "۱ گام" in sentence

    def test_a_goal_without_a_report_stays_honest(self) -> None:
        assert _render_capability("goal", {"steps": 3, "finished": False}, None) == "هدف اجرا شد."


class TestSpeechNarration:
    """The speech outcome — the real-voice line and the blocked-env remedy."""

    def test_a_real_voice_narrates(self) -> None:
        result: dict[str, Any] = {"spoken": True, "voice": "Microsoft Dilnaz"}
        sentence = _render_capability("speech", result, None)
        assert sentence is not None
        assert "با صدای واقعی گفته شد" in sentence
        assert "Dilnaz" in sentence

    def test_the_blocked_env_refusal_carries_the_remedy(self) -> None:
        result: dict[str, Any] = {
            "spoken": False,
            "error": "صدای فارسی روی این ویندوز نصب نیست",
        }
        sentence = _render_capability("speech", result, None)
        assert sentence is not None
        assert "بلند نشد" in sentence
        assert "Settings" in sentence  # the exact remedy, named

    def test_an_unnamed_speech_failure_stays_silent(self) -> None:
        # An unknown failure renders via the honest error line, not a guess.
        result: dict[str, Any] = {"spoken": False, "error": "سازگار نیست"}
        assert _render_capability("speech", result, None) is None

    def test_speech_in_a_full_report(self) -> None:
        payload: dict[str, Any] = {
            "ok": True,
            "route": ["speech"],
            "result": {"speech": {"spoken": True, "voice": "دلناز"}},
            "errors": {},
        }
        report = persian_report(payload)
        assert "با صدای واقعی گفته شد" in report


class TestExcelReadNarration:
    def test_a_read_workbook_narrates_headers(self) -> None:
        result: dict[str, Any] = {
            "headers": ["ماه", "فروش"],
            "rows": [{"ماه": "فروردین", "فروش": 10}, {"ماه": "اردیبهشت", "فروش": 20}],
        }
        sentence = _render_capability("excel", result, None)
        assert sentence is not None
        assert "صفحهگسترده خوانده شد" in sentence
        assert "۲ ردیف" in sentence
        assert "ماه" in sentence and "فروش" in sentence

    def test_an_excel_result_without_headers_or_rows_stays_honest(self) -> None:
        assert _render_capability("excel", {"bytes": 12}, None) is None


class TestSingleMissBranches:
    def test_screenshot_without_a_path_renders_nothing(self) -> None:
        assert _render_capability("screenshot", {"width": 800}, None) is None

    def test_webfetch_without_a_title_names_the_status(self) -> None:
        sentence = _render_capability("webfetch", {"status": 200, "bytes": 5}, None)
        assert sentence is not None
        assert "کد ۲۰۰" in sentence

    def test_a_scanned_pdf_names_its_textless_state(self) -> None:
        sentence = _render_capability("pdfreader", {"text": "", "pages": 3}, None)
        assert sentence is not None
        assert "۳ صفحه" in sentence
        assert "اسکن" in sentence

    def test_an_empty_ocr_names_its_empty_state(self) -> None:
        sentence = _render_capability("ocr", {"text": "", "language": "fa"}, None)
        assert sentence is not None
        assert "متنی در آن پیدا نشد" in sentence

    def test_a_non_dict_result_for_a_dict_capability_renders_nothing(self) -> None:
        # A chart result must be a dict; a str falls through honestly.
        assert _render_capability("chart", "bytes", None) is None


__test__ = True
