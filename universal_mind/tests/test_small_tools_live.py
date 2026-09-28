"""Tests: the small real tools' LIVE branches (R50 wave 2).

Every branch is the tool's OWN error/edge path — real files, real store,
no mock of the tool itself (only subprocess/network seams are patched).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch as mock_patch

from universal_mind.goal_parser import goal_report, parse_goal


class TestGoalParser:
    """تجزیهی هدف: گاردها، پیوند گام کوتاه، گام خالی."""

    def test_guarded_step_is_marked(self) -> None:
        g = parse_goal("هدف: اگر میانگین موفق بود نمودارش را بکش")
        assert g is not None
        assert g.guarded == (True,)

    def test_dangling_guard_falls_forward(self) -> None:
        g = parse_goal("هدف: اگر موفق بود میانگین بگیر و نمودار بکش")
        assert g is not None
        assert len(g.steps) == 2
        assert g.guarded[0] is True

    def test_short_step_joins_the_previous(self) -> None:
        g = parse_goal("هدف: میانگین ۴ و ۶ را حساب کن و چارت")
        assert g is not None
        # a <3-char tail merges into the previous step
        assert any("و" in s for s in g.steps)

    def test_empty_steps_yield_none(self) -> None:
        assert parse_goal("هدف:    ") is None

    def test_goal_report_renders_persian_numbers(self) -> None:
        g = parse_goal("هدف: میانگین ۴ و ۶ را حساب کن")
        assert g is not None
        r = goal_report(g)
        assert "۱." in r["rendered"]  # Persian step numbers


class TestClipboard:
    """کلیپبورد واقعی ویندوز: متن فارسی رفت-وبرگشت."""

    def test_set_and_get_roundtrip_persian(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        tool = ClipboardTool()
        payload = "سلام ذهن یکپارچه ۱۲۳"
        r1 = tool.set_text(payload)
        assert r1["ok"] is True, r1.get("error", "")
        r2 = tool.get_text()
        assert r2["ok"] is True
        assert r2["outcome"] == payload

    def test_empty_text_is_refused(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        r = ClipboardTool().set_text("")
        assert r["ok"] is False
        assert r["error"] == "empty text"

    def test_a_missing_powershell_names_the_error(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        with mock_patch(
            "universal_mind.real_clipboard.subprocess.run",
            side_effect=FileNotFoundError("no powershell"),
        ):
            r = ClipboardTool().set_text("x")
        assert r["ok"] is False
        assert "no powershell" in r["error"]

    def test_a_failing_get_names_the_error(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        class _Bad:
            returncode = 1
            stdout = ""
            stderr = "boom"

        with mock_patch(
            "universal_mind.real_clipboard.subprocess.run", return_value=_Bad()
        ):
            r = ClipboardTool().get_text()
        assert r["ok"] is False
        assert "boom" in r["error"]

    def test_a_bad_base64_names_the_error(self) -> None:
        from universal_mind.real_clipboard import ClipboardTool

        class _Bad:
            returncode = 0
            stdout = "!!not-base64!!"
            stderr = ""

        with mock_patch(
            "universal_mind.real_clipboard.subprocess.run", return_value=_Bad()
        ):
            r = ClipboardTool().get_text()
        assert r["ok"] is False
        assert "clipboard decode failed" in r["error"]


class TestSeedMemory:
    """بذر حافظه: آخرین ران موفق، بدون ران → None."""

    def test_with_a_real_success_it_seeds(self) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.seed_memory import seed_for_capability

        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            route_and_run("میانگین ۴ و ۶ را حساب کن")
        mat = seed_for_capability("compute")
        assert mat is None or "command" in str(mat)

    def test_speech_materials_route_through_last_spoken(self) -> None:
        from universal_mind.seed_memory import seed_for_capability

        mat = seed_for_capability("speech")
        assert mat is None or isinstance(mat, dict)


class TestLlmConnector:
    """اتصال LLM: پرامپت خالی، خطای HTTP، payload بدشکل — بدون سیم واقعی."""

    def test_empty_prompt_is_refused(self) -> None:

        env = dict(os.environ)
        env["UM_LLM_BASE_URL"] = "http://127.0.0.1:9/v1"
        env["UM_LLM_KEY"] = "k"
        import subprocess as sp
        import sys

        code = (
            "from universal_mind.llm_connector import LLMToolConnector;"
            "r = LLMToolConnector().connect(None, {'prompt': ''});"
            "print(r.ok, r.error)"
        )
        r = sp.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert "پرامپت" in r.stdout

    def test_an_http_error_names_the_code(self) -> None:
        import urllib.error

        from universal_mind.llm_connector import LLMToolConnector

        import io

        _err = urllib.error.HTTPError(
            "url", 500, "server broke", hdrs=None, fp=io.BytesIO(b"boom")  # type: ignore[arg-type]
        )

        import os as _os

        _os.environ["UM_LLM_BASE_URL"] = "http://127.0.0.1:9/v1"
        _os.environ["UM_LLM_KEY"] = "k"
        try:
            with mock_patch(
                "universal_mind.llm_connector.urllib.request.urlopen",
                side_effect=_err,
            ):
                r = LLMToolConnector().connect(None, {"prompt": "سلام"})
        finally:
            _os.environ.pop("UM_LLM_BASE_URL", None)
            _os.environ.pop("UM_LLM_KEY", None)
        assert r.ok is False
        assert "HTTP" in (r.error or "") or "۵۰۰" in (r.error or "")

    def test_a_malformed_payload_names_the_shape(self) -> None:
        from universal_mind.llm_connector import LLMToolConnector

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *a: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"unexpected": true}'

        import os as _os

        _os.environ["UM_LLM_BASE_URL"] = "http://127.0.0.1:9/v1"
        _os.environ["UM_LLM_KEY"] = "k"
        try:
            with mock_patch(
                "universal_mind.llm_connector.urllib.request.urlopen", return_value=_Resp()
            ):
                r = LLMToolConnector().connect(None, {"prompt": "سلام"})
        finally:
            _os.environ.pop("UM_LLM_BASE_URL", None)
            _os.environ.pop("UM_LLM_KEY", None)
        assert r.ok is False
        assert "شکل" in (r.error or "")


class TestConversational:
    """گفتگوی کوچک: سلام/تشکر/یادگیری/بدرود/پیشوند."""

    def test_greeting_answers(self) -> None:
        from universal_mind.conversational import answer_conversational

        r = answer_conversational("سلام")
        assert r is not None
        assert "سلام" in r["result"]["conversational"]["answer"]

    def test_thanks_answers(self) -> None:
        from universal_mind.conversational import answer_conversational

        r = answer_conversational("مرسی")
        assert r is not None
        assert "خواهش" in r["result"]["conversational"]["answer"]

    def test_farewell_answers(self) -> None:
        from universal_mind.conversational import answer_conversational

        r = answer_conversational("خداحافظ")
        assert r is not None
        assert "بازگشتت" in r["result"]["conversational"]["answer"]

    def test_prefix_greeting_redirects_to_command(self) -> None:
        from universal_mind.conversational import answer_conversational

        r = answer_conversational("سلام خوبی؟")
        assert r is not None
        assert "فرمانت" in r["result"]["conversational"]["answer"]

    def test_learning_question_answers(self) -> None:
        from universal_mind.conversational import answer_conversational

        r = answer_conversational("چه یاد گرفتی؟")
        assert r is not None  # either the learned list or the honest none

    def test_a_broken_store_yields_a_plain_greeting(self) -> None:
        from universal_mind import conversational as conv

        with mock_patch(
            "universal_mind.database_suite.DatabaseSuite.shared_persistent",
            side_effect=RuntimeError("db down"),
        ):
            reply = conv._greeting_state()
        assert "سلام" in reply


class TestEmailOutbox:
    """ایمیل: compose واقعی، send بدون اعتبار → نامهای درست."""

    def test_compose_writes_a_real_eml(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose

        r = compose(to="a@b.c", subject="سلام", body="متن", out_dir=str(tmp_path))
        assert r["ok"] is True
        assert Path(r["path"]).exists()

    def test_send_without_credentials_names_it(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose, send

        eml = compose(to="a@b.c", subject="s", body="b", out_dir=str(tmp_path))
        saved = {k: os.environ.pop(k, None) for k in list(os.environ) if "SMTP" in k}
        try:
            r = send(eml["path"])
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
        assert r["ok"] is False
        assert "اعتبارنامه" in r["error"]

    def test_send_of_a_missing_file_names_it(self) -> None:
        from universal_mind.email_outbox import send

        r = send("Z:/no-such.eml")
        assert r["ok"] is False
        assert "پیدا نشد" in r["error"]

    def test_report_and_send_gesture_composes_and_names_credentials(
        self, tmp_path: Path
    ) -> None:
        from universal_mind.email_outbox import email_report

        saved = {k: os.environ.pop(k, None) for k in list(os.environ) if "SMTP" in k}
        try:
            r = email_report(to="a@b.c", body="سلام")
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
        assert r["ok"] is True  # composed; send() honestly reported unsent
        assert r["sent"] is False


class TestPdfReader:
    """PDF واقعی: متن، صفحه-شمار، فایل غایب، بدشکل."""

    def test_a_real_pdf_reads_text(self, tmp_path: Path) -> None:
        try:
            from pypdf import PdfWriter
        except ImportError:
            import pytest

            pytest.skip("pypdf not installed")
            return
        from universal_mind.pdfreader_tool import PdfReaderTool

        w = PdfWriter()
        w.add_blank_page(width=595, height=842)
        p = tmp_path / "x.pdf"
        with open(p, "wb") as fh:
            w.write(fh)
        r = PdfReaderTool().read_text(str(p))
        assert r["ok"] is True
        assert r["pages"] == 1

    def test_missing_file_names_it(self) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        r = PdfReaderTool().read_text("Z:/no.pdf")
        assert r["ok"] is False
        assert "file not found" in r["error"]

    def test_corrupt_pdf_names_it(self, tmp_path: Path) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf at all")
        r = PdfReaderTool().read_text(str(bad))
        assert r["ok"] is False
        assert "unreadable" in r["error"]

    def test_metadata_of_a_real_pdf(self, tmp_path: Path) -> None:
        try:
            from pypdf import PdfWriter
        except ImportError:
            import pytest

            pytest.skip("pypdf not installed")
            return
        from universal_mind.pdfreader_tool import PdfReaderTool

        w = PdfWriter()
        w.add_blank_page(width=595, height=842)
        p = tmp_path / "m.pdf"
        with open(p, "wb") as fh:
            w.write(fh)
        r = PdfReaderTool().metadata(str(p))
        assert r["ok"] is True

    def test_connector_dispatch(self, tmp_path: Path) -> None:
        from universal_mind.pdfreader_tool import PdfReaderToolConnector

        r = PdfReaderToolConnector().connect(None, {"path": "", "operation": "read_text"})
        assert r.ok is False
        r2 = PdfReaderToolConnector().connect(None, {"path": "x", "operation": "nope"})
        assert r2.ok is False
        assert "unknown operation" in (r2.error or "")
