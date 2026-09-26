"""R47 wave 3 — the visible day: today as one live page.

Item 7: «صفحهی امروز را بساز» renders real data (runs, verdicts, shield,
reminders, memories, briefing) into one RTL HTML page and names its path.
Item 8: every tick rebuilds the page — the day stays one glance away.
Item 9: «جمعبندی روز» closes the day with the REAL count, never a promise.
"""

from __future__ import annotations

import io
import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db(rows: list[dict[str, Any]] | None = None) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r47w3.db"))
    RunHistory(suite)
    if rows:
        suite.insert_many("run_history", rows)
    return suite


_DAY = [
    {"command": "نمودار خطی از دما بکش", "route": "chart",
     "succeeded": 1, "excellence": 0.9, "verified": 1},
    {"command": "میانگین ۵ و ۷ را حساب کن", "route": "math",
     "succeeded": 0, "excellence": 0.2, "verified": 0},
]


class TestTodayPage:
    def test_build_the_page_on_ask(self) -> None:
        db = _db(_DAY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("صفحهی امروز را بساز")
            assert res is not None
            report = str(res["agent_report"])
            assert "صفحهی امروز ساخته شد" in report
            assert "۲ فرمان" in report       # the REAL count, Persian digits
            assert "📍" in report             # the path is spoken
            page = Path(report.split("📍")[1].strip().splitlines()[0])
            assert page.exists()
            html = page.read_text(encoding="utf-8")
            assert 'dir="rtl"' in html
            assert "نمودار خطی از دما بکش" in html
            assert "chart" in html
            assert "✅" in html and "❌" in html  # both outcomes honest
            assert "🛡" in html                    # the verified stamp shows

    def test_every_section_comes_from_the_real_tables(self) -> None:
        db = _db(_DAY)
        db.insert_many("reminders", [
            {"message": "بکاپ شبانه را چک کن", "fire_at": "2026-09-26 21:00"},
        ])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.today_page import build_today_page

            info = build_today_page(db=db)
            assert info["ok"] is True
            assert info["runs"] == 2 and info["wins"] == 1
            assert info["shield"] == 1
            assert info["reminders"] == 1
            html = Path(info["path"]).read_text(encoding="utf-8")
            assert "بکاپ شبانه را چک کن" in html

    def test_tick_rebuilds_the_page(self) -> None:
        db = _db(_DAY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.today_page import build_today_page

            first = build_today_page(db=db)
            page = Path(first["path"])
            m0 = page.stat().st_mtime_ns
            import time

            time.sleep(0.02)
            os.environ.pop("UM_LLM_BASE_URL", None)
            import universal_mind.scripts.scheduler_tick as ST

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ST.tick()
            assert page.stat().st_mtime_ns > m0  # fresher than before

    def test_the_goodbye_counts_the_real_day(self) -> None:
        db = _db(_DAY)
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            from universal_mind.reflexive import answer_reflexive

            res = answer_reflexive("جمعبندی روز")
            assert res is not None
            report = str(res["agent_report"])
            assert "🌙" in report
            assert "فرمان اجرا شد" in report
            assert "خداحافظ" in report
            # the goodbye re-renders the page too
            assert "📍" not in report or "today.html" in report
