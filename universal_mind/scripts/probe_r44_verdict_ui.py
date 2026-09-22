#!/usr/bin/env python3
"""Probe: R44 item 4 — the one-click verdict in both faces.

Live laws:
1. The desktop chat packs real 👍/👎 buttons under a successful run, and a
   click lands a store-bound verdict row (verdict='good').
2. The web face /verdict endpoint records the SAME record_verdict —
   the human's click in a browser equals their typed «عالی بود».
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-4 (verdict buttons in both faces):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import json
    import tempfile
    import threading
    import time
    import urllib.parse
    import urllib.request
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r44-4.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        route_and_run("میانگین ۴ و ۶ را حساب کن")  # a real success to rule on

        # H1 — desktop: buttons appear, a click records the bound verdict.
        import tkinter as tk
        import tkinter.ttk as ttk

        from universal_mind.desktop_app import MindDesktopApp

        root = tk.Tk()
        root.withdraw()
        app = MindDesktopApp(root)
        try:
            app._show_verdict_buttons("میانگین ۴ و ۶ را حساب کن")
            labels = [
                w.cget("text") for w in app._verdict_bar.winfo_children()
                if isinstance(w, ttk.Button)
            ]
            _ok("desktop shows 👍/👎", any("عالی بود" in t for t in labels) and any("بد بود" in t for t in labels))
            good = next(w for w in app._verdict_bar.winfo_children()
                        if isinstance(w, ttk.Button) and "عالی بود" in w.cget("text"))
            good.invoke()  # the human clicks
            rows = iso.query("SELECT verdict FROM operator_verdicts")["rows"]
            _ok("click lands a bound verdict row",
                bool(rows) and rows[0]["verdict"] == "good", f"rows={len(rows)}")
        finally:
            root.destroy()

        # H2 — remote: /verdict records the same store-bound verdict.
        from universal_mind.remote_face import serve

        srv = serve(8797)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        time.sleep(0.4)
        try:
            q = urllib.parse.quote("میانگین ۴ و ۶ را حساب کن")
            r = urllib.request.urlopen(
                f"http://127.0.0.1:8797/verdict?text={q}&v=bad", timeout=10
            )
            out = json.loads(r.read().decode("utf-8"))
            _ok("web /verdict records honestly", out.get("ok") is True, str(out.get("answer"))[:40])
            n = iso.query("SELECT COUNT(*) AS n FROM operator_verdicts")["rows"][0]["n"]
            _ok("both faces share one store", int(n) >= 2, f"total verdicts={n}")
        finally:
            srv.shutdown()
            srv.server_close()

    sys.stderr.write("R44-4: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
