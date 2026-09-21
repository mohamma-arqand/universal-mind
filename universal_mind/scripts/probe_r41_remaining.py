#!/usr/bin/env python3
"""Probe: R41 — the remaining-work audit closed. The tick installed, the
context GC sliding, the honest named failure, the goal store clean, and the
localhost face serving. All live in the gate."""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R41 remaining work:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    # e4 — the tick installed (read back through schtasks).
    from universal_mind.task_install import tick_health

    h = tick_health()
    _ok("tick installed", bool(h.get("signals", {}).get("task_installed")),
        f"verdict={h.get('verdict')}")

    # e2 — the retention GC slides the window.
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.conversation_memory import KEEP_ROWS, save_context
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-ctx.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite)):
        for i in range(KEEP_ROWS + 10):
            save_context(f"فرمان {i}", ["data"], {})
    q = suite.query("SELECT COUNT(*) AS n FROM last_context")
    _ok("context GC keeps window", q["rows"][0]["n"] == KEEP_ROWS,
        f"rows={q['rows'][0]['n']}")

    # e1 — the goal store carries no junk rows (nested/zzqx test goals).
    from universal_mind.database_suite import DatabaseSuite as DS

    q2 = DS.shared_persistent().query(
        "SELECT COUNT(*) AS n FROM goals "
        "WHERE goal LIKE '%هدف: هدف:%' OR goal LIKE '%zzqx%'"
    )
    _ok("goal store clean", q2["rows"][0]["n"] == 0, f"junk={q2['rows'][0]['n']}")

    # e5 — the honest named failure (the refusal with the remedy).
    from universal_mind.persian_report import persian_report

    out = persian_report({
        "ok": False, "route": [], "result": {},
        "errors": {"speech": "صدای فارسی روی این ویندوز نصب نیست — نصب کن"},
    })
    _ok("honest named failure", "صدای فارسی" in out)

    # e6 — the localhost face serves a real ask round-trip.
    import json
    import threading
    import time
    import urllib.parse
    import urllib.request

    from universal_mind.remote_face import serve

    srv = serve(8793)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    try:
        q3 = urllib.parse.quote("میانگین ۵ و ۷ را حساب کن")
        r = urllib.request.urlopen(f"http://127.0.0.1:8793/ask?text={q3}", timeout=30)
        p = json.loads(r.read().decode("utf-8"))
        _ok("remote face ask", bool(p.get("ok")) and p.get("route") == ["data"],
            f"route={p.get('route')}")
    finally:
        srv.shutdown()
        srv.server_close()

    sys.stderr.write("R41 remaining work: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())