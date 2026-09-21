"""Tests: R41 — the remote face (localhost API over the Persian router),
the last_context retention GC, and the honest named failure."""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

from universal_mind.conversation_memory import KEEP_ROWS, save_context
from universal_mind.database_suite import DatabaseSuite


def _isolated_ctx() -> Any:
    import tempfile

    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "ctx.db"))
    return mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite))


# ---------- e2: the retention GC ----------
def test_last_context_keeps_only_the_window() -> None:
    import tempfile

    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "ctx2.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite)):
        for i in range(KEEP_ROWS + 15):
            save_context(f"فرمان {i}", ["data"], {"i": i})
    q = suite.query("SELECT COUNT(*) AS n FROM last_context")
    assert q["rows"][0]["n"] == KEEP_ROWS
    # the NEWEST survives (the window slides, the read stays correct)
    q2 = suite.query("SELECT command FROM last_context ORDER BY id DESC LIMIT 1")
    assert q2["rows"][0]["command"] == f"فرمان {KEEP_ROWS + 14}"


# ---------- e5: the honest named failure ----------
def test_report_names_the_real_error() -> None:
    from universal_mind.persian_report import persian_report

    payload = {
        "ok": False,
        "route": [],
        "result": {},
        "errors": {"speech": "صدای فارسی روی این ویندوز نصب نیست — نصب کن"},
    }
    out = persian_report(payload)
    assert "صدای فارسی" in out  # the refusal is NAMED, not 'علت نامشخص'


# ---------- e6: the remote face ----------
def test_remote_face_serves_ask_health_and_page() -> None:
    from universal_mind.remote_face import serve

    srv = serve(8791)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.4)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8791/health", timeout=5)
        assert r.status == 200
        assert json.loads(r.read().decode())["ok"] is True

        q = urllib.parse.quote("میانگین ۵ و ۷ را حساب کن")
        r2 = urllib.request.urlopen(f"http://127.0.0.1:8791/ask?text={q}", timeout=30)
        p = json.loads(r2.read().decode("utf-8"))
        assert p["ok"] is True
        assert p["route"] == ["data"]
        assert p.get("agent_report")

        r3 = urllib.request.urlopen("http://127.0.0.1:8791/", timeout=5)
        page = r3.read().decode("utf-8")
        assert "ذهن جهانی" in page
        assert r3.status == 200
    finally:
        srv.shutdown()
        srv.server_close()


def test_remote_face_honest_on_unknown() -> None:
    from universal_mind.remote_face import serve

    srv = serve(8792)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.4)
    try:
        q = urllib.parse.quote("zzqx qwerty")
        r = urllib.request.urlopen(f"http://127.0.0.1:8792/ask?text={q}", timeout=30)
        p = json.loads(r.read().decode("utf-8"))
        assert p["ok"] is False  # the router's honest failure, verbatim
        assert p.get("agent_report")
    finally:
        srv.shutdown()
        srv.server_close()