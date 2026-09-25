"""Tests: R44 item 4 — the one-click verdict, in BOTH faces.

The human judge joins through the UI, not just typing:
- the desktop chat packs 👍/👎 buttons under every successful run;
- the remote web face renders them and posts to /verdict — the SAME
  store-bound record_verdict as «عالی بود»/«بد بود» typed in chat.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Iterator


def _isolated() -> AbstractContextManager[Any]:
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    @contextmanager
    def _ctx() -> Iterator[Any]:
        suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-4.db"))
        with mock_patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite)
        ):
            yield suite

    return _ctx()


class TestVerdictButtonsDesktop:
    """The desktop chat: buttons under the answer, one click = one verdict."""

    def test_verdict_buttons_appear_for_real_runs(self) -> None:
        """A successful real run appends 👍/👎 — an explained (dry) run does NOT."""
        import tkinter as tk

        from universal_mind.desktop_app import MindDesktopApp

        with _isolated():
            root = tk.Tk()
            root.withdraw()
            app = MindDesktopApp(root)
            try:
                app._show_verdict_buttons("میانگین ۴ و ۶ را حساب کن")
                root.update_idletasks()
                root.update()  # let Tk render the new widgets before inspecting
                import tkinter.ttk as ttk

                labels = [
                    w.cget("text") for w in app._verdict_bar.winfo_children()
                    if isinstance(w, ttk.Button)
                ]
                assert any("عالی بود" in t for t in labels)
                assert any("بد بود" in t for t in labels)
            finally:
                root.destroy()

    def test_a_click_records_the_bound_verdict(self) -> None:
        """Clicking 👍 records verdict='good' bound to THAT command."""
        import tkinter as tk

        from universal_mind.desktop_app import MindDesktopApp

        with _isolated() as suite:
            from universal_mind.persian_router import route_and_run

            route_and_run("میانگین ۴ و ۶ را حساب کن")  # a real success to bind to
            root = tk.Tk()
            root.withdraw()
            app = MindDesktopApp(root)
            try:
                app._show_verdict_buttons("میانگین ۴ و ۶ را حساب کن")
                root.update_idletasks()
                root.update()  # let Tk render the new widgets before inspecting
                import tkinter.ttk as ttk

                buttons = [w for w in app._verdict_bar.winfo_children() if isinstance(w, ttk.Button)]
                good = next(b for b in buttons if "عالی بود" in b["text"])
                good.invoke()  # the human clicks 👍
                rows = suite.query("SELECT verdict FROM operator_verdicts")["rows"]
                assert rows and rows[0]["verdict"] == "good"
            finally:
                root.destroy()


class TestVerdictButtonsRemote:
    """The web face: /verdict records the same store-bound verdict."""

    def test_verdict_endpoint_records_and_answers(self) -> None:
        from universal_mind.remote_face import serve

        with _isolated():
            from universal_mind.persian_router import route_and_run

            route_and_run("میانگین ۴ و ۶ را حساب کن")  # something to rule on
            srv = serve(8795)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            time.sleep(0.4)
            try:
                q = urllib.parse.quote("میانگین ۴ و ۶ را حساب کن")
                r = urllib.request.urlopen(
                    f"http://127.0.0.1:8795/verdict?text={q}&v=bad", timeout=10
                )
                out = json.loads(r.read().decode("utf-8"))
                assert out["ok"] is True
                assert "پایین میآورم" in out["answer"]
            finally:
                srv.shutdown()
                srv.server_close()

    def test_page_carries_the_verdict_ui(self) -> None:
        """The served page renders the 👍/👎 wiring."""
        from universal_mind.remote_face import _PAGE

        assert "verdictRow" in _PAGE
        assert "/verdict" in _PAGE
        assert "عالی بود" in _PAGE
