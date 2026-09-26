"""R47 wave 1 — the live judge: a second opinion from a real model.

Item 1: judge_live refuses honestly without env, parses a real reply,
and stores the two scores side by side.
Item 2: the ⚖ داورِ زنده line rides the report only when env is wired.
Item 3: each tick samples ONE successful run of today for the judge.
"""

from __future__ import annotations

import json as J
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import mkdtemp
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db() -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(mkdtemp()) / "r47w1.db"))
    RunHistory(suite)
    return suite


def _server(reply_score: float, reply_reason: str) -> tuple[HTTPServer, str]:
    """A real local OpenAI-compatible endpoint — never a mock object.

    ThreadingHTTPServer + server_close(): the single-threaded HTTPServer
    on Windows sometimes aborts an in-flight connection during back-to-back
    server churn (WinError 10053) — a thread-per-request server with its
    socket explicitly closed keeps the five wave-1 tests deterministic.
    """

    class H(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = J.dumps({"choices": [{"message": {"content": J.dumps(
                {"score": reply_score, "reason": reply_reason})}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a: Any) -> None:
            pass

    from http.server import ThreadingHTTPServer

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/v1"


class TestLiveJudge:
    def test_no_env_refuses_honestly(self) -> None:
        import os

        db = _db()
        with patch.object(DatabaseSuite, "shared_persistent",
                           classmethod(lambda cls: db)):
            os.environ.pop("UM_LLM_BASE_URL", None)
            from universal_mind.live_judge import judge_live

            res = judge_live("نمودار از ۲ بکش", "نمودار ساخته شد", 0.8)
            assert res["ok"] is False
            assert "در دسترس نیست" in res["reason"]
            rows = db.query("SELECT COUNT(*) AS n FROM live_judgments")
            assert rows["rows"][0]["n"] == 0  # nothing stored on refusal

    def test_real_reply_stores_two_scores(self) -> None:
        import os

        db = _db()
        srv, url = _server(0.91, "اجرا کامل و صادق بود")
        try:
            with patch.object(DatabaseSuite, "shared_persistent",
                              classmethod(lambda cls: db)):
                os.environ["UM_LLM_BASE_URL"] = url
                from universal_mind.live_judge import judge_live

                res = judge_live("نمودار از ۲ بکش", "نمودار ساخته شد", 0.3)
                assert res["ok"] is True
                assert res["llm_score"] == 0.91
                assert res["diverged"] is True  # |0.91 - 0.3| = 0.61 > 0.3
                row = db.query(
                    "SELECT command, formula_score, llm_score, reason "
                    "FROM live_judgments"
                )["rows"][0]
                assert row["command"] == "نمودار از ۲ بکش"
                assert abs(float(row["formula_score"]) - 0.3) < 1e-6
                assert abs(float(row["llm_score"]) - 0.91) < 1e-6
                assert "صادق" in str(row["reason"])
        finally:
            os.environ.pop("UM_LLM_BASE_URL", None)
            srv.shutdown()
            srv.server_close()

    def test_malformed_reply_is_refused_not_guessed(self) -> None:
        import os

        db = _db()

        class H(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = J.dumps({"choices": [{"message": {
                    "content": "من فقط متن آزاد هستم بدون JSON"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a: Any) -> None:
                pass

        from http.server import ThreadingHTTPServer

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with patch.object(DatabaseSuite, "shared_persistent",
                              classmethod(lambda cls: db)):
                os.environ["UM_LLM_BASE_URL"] = (
                    f"http://127.0.0.1:{srv.server_port}/v1")
                from universal_mind.live_judge import judge_live

                res = judge_live("نمودار از ۲ بکش", "گزارش", 0.5)
                assert res["ok"] is False
                assert "شکلِ شناخته" in res["reason"]
                rows = db.query("SELECT COUNT(*) AS n FROM live_judgments")
                assert rows["rows"][0]["n"] == 0
        finally:
            os.environ.pop("UM_LLM_BASE_URL", None)
            srv.shutdown()
            srv.server_close()

    def test_report_line_rides_only_with_env(self) -> None:
        import os

        db = _db()
        srv, url = _server(0.92, "نمودار واقعی و گزارش صادق است")
        try:
            with patch.object(DatabaseSuite, "shared_persistent",
                              classmethod(lambda cls: db)):
                from universal_mind.persian_router import route_and_run

                os.environ.pop("UM_LLM_BASE_URL", None)
                without = route_and_run("نمودار از ۲ و ۳ بکش")
                assert "⚖ داورِ زنده" not in str(without.get("agent_report"))

                os.environ["UM_LLM_BASE_URL"] = url
                with_env = route_and_run("نمودار دایرهای از ۲ و ۵ بکش")
                report = str(with_env.get("agent_report"))
                assert "⚖ داورِ زنده" in report
                assert "۰٫" in report or "۰." in report  # the score is spoken
                assert "نمودار واقعی" in report  # the reason is spoken too
        finally:
            os.environ.pop("UM_LLM_BASE_URL", None)
            srv.shutdown()
            srv.server_close()

    def test_tick_samples_one_run_of_today(self) -> None:
        import io
        import contextlib
        import os

        db = _db()
        srv, url = _server(0.88, "زنجیره سالم و مفید بود")
        try:
            with patch.object(DatabaseSuite, "shared_persistent",
                              classmethod(lambda cls: db)):
                from universal_mind.persian_router import route_and_run

                os.environ["UM_LLM_BASE_URL"] = url
                route_and_run("نمودار از ۲ و ۳ بکش")
                # the tick's own canary run also earns the ⚖ line (item 2),
                # so count judgments of THE sampled command, not the table.
                before = db.query(
                    "SELECT COUNT(*) AS n FROM live_judgments "
                    "WHERE command = 'نمودار از ۲ و ۳ بکش'"
                )["rows"][0]["n"]

                import universal_mind.scripts.scheduler_tick as ST

                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ST.tick()
                out = buf.getvalue()
                after = db.query(
                    "SELECT COUNT(*) AS n FROM live_judgments "
                    "WHERE command = 'نمودار از ۲ و ۳ بکش'"
                )["rows"][0]["n"]
                assert after == before + 1  # exactly one sampled verdict
                assert "داورِ زنده" in out
                assert "زنجیره سالم" in out  # the reason is printed
        finally:
            os.environ.pop("UM_LLM_BASE_URL", None)
            srv.shutdown()
            srv.server_close()
