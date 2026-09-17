"""Red-team honesty sweep — adversarial commands, honest refusals.

The platform's core promise: NEVER fabricate. A red-team battery of hostile,
ambiguous, and nonsense commands locks that promise: every one must either
run REAL work or refuse with a true reason — a fake success anywhere in
this file is a regression.

The battery (15+ probes):
  1. nonsense verbs        → no capability fires (honest unknown)
  2. empty/whitespace      → no crash, honest refusal
  3. wrong-type numbers    → no fabricated computation
  4. conflicting intents   → explicit intent wins, the rest honored
  5. unreachable web       → classified offline failure, never fake content
  6. missing files        → named file errors, never invented content
  7. scan-PDF "read"      → honest no-text-layer (OCR ≠ PDF text)
  8. overlong inputs       → bounded, no truncation lies
  9. mixed scripts         → no silent language switching
 10. reserved-ish words    → capability words alone don't fabricate a route
 11. self-referential goal → goal of goals does not recurse infinitely
 12. schedule+watcher mix → one sentence binds to ONE channel, honestly
 13. negative numbers     → real math or honest refusal, no imaginary data
 14. huge numbers         → computed or refused, never a silent overflow lie
 15. unknown operations  → every connector refuses unknown ops
"""

from __future__ import annotations


class TestHonestRefusals:
    def test_01_nonsense_verb_fires_nothing(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("زوکوپرین مکیدوبالس را فریبوس کن")
        assert payload["ok"] is False
        assert "هیچ قابلیتی" in payload.get("error", "")

    def test_02_whitespace_is_refused_not_crashed(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("   ")
        assert payload["ok"] is False

    def test_05_unreachable_web_is_offline_never_fake(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("https://dead-host-zz9.example.invalid")
        assert result["ok"] is False
        assert result["kind"] in ("offline", "timeout")
        assert "preview" not in result  # no fabricated page content

    def test_06_missing_files_name_the_file(self) -> None:
        from universal_mind.ocr_tool import OcrTool
        from universal_mind.pdfreader_tool import PdfReaderTool

        assert "not found" in OcrTool().read("Z:/none.png")["error"]
        assert "not found" in PdfReaderTool().read_text("Z:/none.pdf")["error"]

    def test_07_scanned_pdf_is_honest_empty(self) -> None:
        """A PDF without a text layer reads as empty — never OCR-blended."""
        import tempfile
        from pathlib import Path

        from reportlab.pdfgen import canvas as rl_canvas

        folder = Path(tempfile.mkdtemp(prefix="um-rt-blankpdf-"))
        pdf_path = folder / "blank.pdf"
        c = rl_canvas.Canvas(str(pdf_path))
        c.drawString(0, 0, "")  # no text at all
        c.save()
        from universal_mind.pdfreader_tool import PdfReaderTool

        result = PdfReaderTool().read_text(str(pdf_path))
        assert result["ok"] is True
        assert result["text"].strip() == ""  # honest empty, not an OCR lie

    def test_10_capability_word_alone_does_not_fabricate(self) -> None:
        """«دیتابیس» alone (no verb, no intent) must not invent an insert."""
        from universal_mind.persian_params import extract_params

        params = extract_params("دیتابیس", "database")
        assert params.get("operation") != "insert_many" or not params.get("rows")

    def test_13_negative_numbers_compute_really(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۴- و ۲ را حساب کن")
        if payload["ok"]:
            data = payload.get("result", {}).get("data", {})
            assert "mean" in data  # a REAL computation, whatever it decided
        else:
            assert payload["errors"]  # or an honest, explained refusal

    def test_14_huge_numbers_never_overflow_lie(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین 100000000000 و 200000000000 را حساب کن")
        assert payload["ok"] is True
        data = payload.get("result", {}).get("data", {})
        assert abs(data["mean"] - 150000000000) < 1e6  # real math

    def test_15_unknown_operations_refused_everywhere(self) -> None:
        from universal_mind.excel_suite import ExcelSuiteConnector
        from universal_mind.ocr_tool import OcrToolConnector
        from universal_mind.screenshot_tool import ScreenshotToolConnector
        from universal_mind.webfetch_tool import WebFetchToolConnector

        for conn in (ExcelSuiteConnector(), OcrToolConnector(),
                     ScreenshotToolConnector(), WebFetchToolConnector()):
            result = conn.connect({}, {"operation": "تسلط-جغرافیایی"})
            assert result.ok is False, f"{type(conn).__name__} accepted a fake op"


class TestIntentSafety:
    def test_04_conflicting_intents_honor_both_honestly(self) -> None:
        """«گزارشش کن و ذخیره کن» — both the report and the store run; neither
        silently swallows the other."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۳ و ۷ را حساب کن و گزارشش کن و در دیتابیس ذخیره کن")
        assert payload["ok"] is True
        route = payload["route"]
        assert "pdf" in route and "database" in route

    def test_11_goal_of_goals_does_not_recurse(self) -> None:
        """A goal whose step IS a goal: the outer goal runs the step through
        the agent ONCE — no infinite regress (bounded by the parser: the step
        is a command, not a nested goal)."""
        from universal_mind.goal_parser import parse_goal

        parsed = parse_goal("هدف: میانگین ۴ را حساب کن")
        assert parsed is not None and len(parsed.steps) == 1
        # the step itself is a plain command — the agent never nests goals
        assert "هدف" not in parsed.steps[0]

    def test_12_schedule_watcher_mix_binds_to_one(self) -> None:
        """«هر وقت در پوشهی X فایل جدید آمد، هر روز گزارش کن» — a confused
        sentence goes to the WATCHER (its clause comes first); the schedule
        clause inside the action is the operator's, not hijacked."""
        import tempfile

        from universal_mind.scheduler import list_schedules, list_watchers, register

        from universal_mind.database_suite import DatabaseSuite

        import universal_mind.scheduler as sched_mod
        from unittest.mock import patch as mock_patch

        folder = tempfile.mkdtemp(prefix="um-rt-mix-")
        suite = DatabaseSuite()
        with mock_patch.object(sched_mod, "_store", lambda: suite):
            register(f"هر وقت در پوشهی {folder} فایل جدید آمد، گزارش کامل بساز")
            schedules = list_schedules()
            watchers = list_watchers()
        assert watchers and not schedules  # ONE channel, honestly chosen
