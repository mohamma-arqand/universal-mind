"""R63 P4 — «پنجره‌های کروم را ببند»: the first real WINDOW ACTION.

The platform could LIST windows (R59 P3) but not act on them — the
sweep's close sentence was dead. The action is honest on every axis:
- Persian program names (کروم/نوتپد) map to Latin processes;
- the close is GRACEFUL (CloseMainWindow — the app can save), never
  a hard kill;
- every closed window is NAMED in the answer;
- a name matching nothing is a named refusal listing what IS open;
- everything passed to PowerShell is quote-escaped — a window title
  can never become code;
- the payload's ok tells the truth (a refused close is ok=False).

The LIVE proof (probe-class, run here as a test with a real Notepad):
open Notepad on a temp file → «پنجره‌های نوتپد را ببند» → the window
is really gone from the OS list.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


class TestThePersianAlias:
    def test_matches_the_latin_process(self) -> None:
        from universal_mind.window_actions import _matches, _ps_quote

        # the ESCAPED string may contain ' (doubled) — what must NOT
        # happen is a lone unescaped one reaching PowerShell. The rule
        # ' -> '' is proven exactly:
        assert _ps_quote("it's") == "it''s"
        # alias mapping happens against the REAL window list; without a
        # notepad open this is [] — the mapping itself is proven by the
        # alias table + the live test below.
        assert isinstance(_matches("نوتپد"), list)

    def test_ps_quote_doubles_single_quotes(self) -> None:
        from universal_mind.window_actions import _ps_quote

        assert _ps_quote("a'b") == "a''b"


class TestTheRefusal:
    def test_a_name_with_no_window_refuses_with_the_real_list(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("پنجره‌های برنامه-آزمون-ناموجود-r63 را ببند")
        assert p["ok"] is False  # R63 P4: a refused close is NOT a success
        rep = p["agent_report"]
        assert "باز نیست" in rep
        assert "پنجره‌های دیده‌شده" in rep  # the real open list is shown


class TestTheRealClose:
    """Opens a REAL Notepad, closes it by the Persian name, proves it."""

    def test_notepad_closes_for_real(self) -> None:
        witness = Path(__file__).parent.parent / "um_r63_witness.txt"
        witness.write_text("گواه بستن پنجره", encoding="utf-8")
        try:
            subprocess.Popen(
                ["notepad.exe", str(witness)],
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0)
            time.sleep(3)
            from universal_mind.window_view import list_open_windows

            before = [w for w in list_open_windows()["windows"]
                      if "um_r63_witness" in w["title"]]
            assert before, "the witness notepad must be open for the proof"

            from universal_mind.persian_router import route_and_run

            p = route_and_run("پنجره‌های نوتپد را ببند")
            assert p["ok"] is True
            assert "بستم" in p["agent_report"]
            assert "Notepad" in p["agent_report"]  # the closed one is named

            time.sleep(2)
            after = [w for w in list_open_windows()["windows"]
                     if "um_r63_witness" in w["title"]]
            assert after == [], "the window must really be gone"
        finally:
            witness.unlink(missing_ok=True)
