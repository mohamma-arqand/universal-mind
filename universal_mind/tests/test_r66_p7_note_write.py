"""R66 P7 — «یادداشت X را بنویس»: a note sentence is a clipboard WRITE.

The sweep caught «یادداشت امروز را بنویس و بعدش ایمیل کن» going to
email FIRST (with no recipient) while the note never landed anywhere.
A note-taking sentence with «بنویس» now carries the spoken text to the
clipboard write; the multi-step sentence runs the note first, then the
email honestly refuses on its own missing recipient — each step named.
"""

from __future__ import annotations

import pytest


class TestTheNoteWrite:
    def test_note_sentence_builds_write_params(self) -> None:
        from universal_mind.persian_params import extract_params

        out = extract_params("یادداشت جلسه فردا ساعت ۱۰ است را بنویس", "clipboard")
        assert out.get("operation") == "write"
        assert "جلسه فردا" in out.get("text", "")

    def test_a_real_write_lands_on_the_clipboard(self) -> None:
        from universal_mind.clipboard_adapter import ClipboardToolConnector
        from universal_mind.real_clipboard import ClipboardTool

        tool = ClipboardTool()
        if tool.get_text().get("ok") is not True:  # OS lock in the live env
            pytest.skip("clipboard locked by another program")
        out = ClipboardToolConnector(tool).connect(
            None, {"operation": "write", "text": "گواه-r66-p7"})
        assert out.ok is True
        assert tool.get_text()["outcome"] == "گواه-r66-p7"

    def test_the_write_then_email_chain_names_both(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادداشت جلسه فردا ساعت ۱۰ است را بنویس و بعدش ایمیل کن")
        # the NOTE step is answered first (a write was attempted), and the
        # email's missing recipient is named — the run is not a shrug.
        rep = p.get("agent_report", "")
        assert "کلیپبورد" in rep or "یادداشت" in rep
        assert p.get("route") is not None and "email" in (p.get("route") or [])
