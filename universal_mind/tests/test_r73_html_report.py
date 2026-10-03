"""R73 P1-P4 — the HTML REPORT class (the 29th real capability).

A live sweep found «گزارش HTML بساز» handing the operator a PDF (the
«گزارش» keyword routes to pdf; nobody read the FORMAT word). The class:
- html-report route: the sentence's format word decides (HTML never
  builds a PDF; a PDF ask still gets its PDF).
- five REAL views from MEASURED data: report, dashboard, timeline,
  table, card — each names its real path+size.
- the build verbs close the reflexive/list gates («تایم‌لاین کارهای
  امروز بساز» was answered by the day-stats reflex; «جدول از یادآورهای
  من بساز» was answered by the plain list).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_PAGES = ("report", "dashboard", "timeline", "table", "card")


def _cleanup() -> None:
    for name in ("html_report.html", "status_card.html", "timeline_view.html",
                 "table_view.html"):
        try:
            (Path("artifacts") / name).unlink(missing_ok=True)
        except OSError:
            pass


class TestHtmlReport:
    def test_an_html_ask_never_builds_a_pdf(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("گزارش HTML بساز")
        assert p["route"] == ["html-report"], p["route"]
        assert "pdf" not in p["route"], "HTML ask must not build a PDF"

    def test_every_view_builds_a_real_file_with_real_data(self) -> None:
        from universal_mind.persian_router import route_and_run

        asks = {
            "report": "گزارش HTML بساز",
            "dashboard": "داشبورد بساز",
            "timeline": "تایم‌لاین کارهای امروز بساز",
            "table": "جدول از یادآورهای من بساز",
            "card": "کارت وضعیت بساز",
        }
        for mode, cmd in asks.items():
            p = route_and_run(cmd)
            assert p["ok"] is True, (mode, str(p.get("agent_report"))[:80])
            assert p["route"] == ["html-report"], (mode, p["route"])
            rep = str(p.get("agent_report", ""))
            assert "کیلوبایت" in rep and "«" in rep, (mode, rep[:80])
            assert Path("artifacts").exists()

    def test_the_report_names_its_real_path_and_size(self) -> None:
        from universal_mind.html_report import build_html_report

        out = build_html_report()
        assert out["ok"] is True
        f = Path(out["path"])
        assert f.exists() and f.stat().st_size == out["bytes"]
        body = f.read_text(encoding="utf-8")
        assert "<html" in body and 'dir="rtl"' in body
        assert "قابل خواندن نیست" in body or "رم" in body  # honesty lines

    def test_a_pdf_ask_still_gets_its_pdf(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("گزارش PDF بساز")
        assert p["ok"] is True
        assert "pdf" in p["route"] and "html-report" not in p["route"]

    def test_build_verbs_close_the_reflexive_gate(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        assert answer_reflexive("تایم‌لاین کارهای امروز بساز") is None
        assert answer_reflexive("وضعیت کلی من چطور است؟") is not None

    def test_the_plain_list_still_lists(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآورهای من")
        assert p["ok"] is True
        assert "html-report" not in p["route"]

    def test_the_connector_speaks_the_protocol(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.html_report_connector import HtmlReportConnector

        conn = HtmlReportConnector()
        out = conn.connect(None, {"mode": "card"})
        assert isinstance(out, ConnectorResult)
        assert out.ok is True and Path(out.output["path"]).exists()
        bad = conn.connect(None, {"mode": "no-such-mode"})
        # unknown mode falls back to the report — never a crash
        assert bad.ok is True


@pytest.fixture(autouse=True)
def _around() -> None:
    _cleanup()
    yield
    _cleanup()
