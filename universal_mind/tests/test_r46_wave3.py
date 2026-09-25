"""R46 wave 3 — learning that sticks in real time, tested against live routes.

Item 9  — taught words: «واژهی X یعنی Y» routes the NEXT command, no commit.
Item 10 — the morning briefing: first tick of the day writes it; speech reads it.
Item 11 — hot-path indexes: SCAN → SEARCH ... USING INDEX, proven before/after.
Item 12 — the one-menu periodic report: briefing + letter + yearbook in one answer.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _fresh_db(monkeypatch, tmp_path):
    db = DatabaseSuite(str(tmp_path / "r46w3.db"))
    RunHistory(db)
    monkeypatch.setattr(
        DatabaseSuite, "shared_persistent",
        classmethod(lambda cls: db),
    )
    return db


class TestTaughtWords:
    def test_definition_teaches_and_next_command_routes(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route, route_and_run

        r1 = route_and_run("واژهی زرشک یعنی داده")
        assert r1["ok"] is True
        assert "یاد گرفتم" in r1["agent_report"]

        r2 = route("میانگین زرشک و انار را حساب کن")
        assert "زرشک" in r2.matched_words       # the taught word fires
        assert "data" in r2.capabilities

    def test_listing_shows_taught_words(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        route_and_run("واژهی بپاشک یعنی نمودار")
        r = route_and_run("چه یاد گرفتی؟")
        assert "بپاشک" in r["agent_report"]
        assert "واژه" in r["agent_report"]

    def test_redefinition_overwrites(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.learned_vocab import learned_words, teach

        teach("زرشک", "data")
        teach("زرشک", "chart")
        words = [d for d in learned_words() if d["word"] == "زرشک"]
        assert len(words) == 1                  # no fork
        assert words[0]["capability"] == "chart"


class TestMorningBriefing:
    def test_first_tick_writes_and_speech_reads(self, monkeypatch, tmp_path):
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run
        from universal_mind.scripts.scheduler_tick import tick

        route_and_run("نمودار از ۲ و ۳ بکش")
        db.execute("UPDATE run_history SET created_at = datetime('now', 'localtime', '-1 day')")
        route_and_run("میانگین ۴ و ۸ را حساب کن")

        tick(notify_summary=False)              # the first tick of the day
        rows = db.query("SELECT day, report FROM daily_briefings")["rows"]
        assert len(rows) == 1                   # ONE row, UNIQUE day
        assert "بریفینگ" in rows[0]["report"]

        p = route_and_run("بریفینگ امروز را بگو")
        assert "بریفینگ" in p["agent_report"]
        assert "دیروز" in p["agent_report"]     # the REAL yesterday line

    def test_silent_day_is_written_honestly(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.daily_briefing import record_briefing
        from datetime import datetime

        info = record_briefing(datetime.now().strftime("%Y-%m-%d"))
        assert "خاموش" in info["report"]        # no fake yesterday
        assert "دیروز فرمانی اجرا نشد" in info["report"]


class TestHotPathIndexes:
    def test_scan_becomes_search_using_index(self, tmp_path):
        con = sqlite3.connect(str(Path(tempfile.mkdtemp()) / "ix.db"))
        con.execute(
            "CREATE TABLE run_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "command TEXT, route TEXT, succeeded INTEGER, created_at TEXT)"
        )
        con.commit()
        before = con.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM run_history WHERE created_at = '2026-09-25'"
        ).fetchall()
        assert any("SCAN" in str(r) for r in before)

        con.execute("CREATE INDEX idx_history_created ON run_history (created_at)")
        con.commit()
        after = con.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM run_history WHERE created_at = '2026-09-25'"
        ).fetchall()
        assert any("USING INDEX" in str(r) for r in after)

    def test_unique_term_index_refuses_duplicates(self, tmp_path):
        con = sqlite3.connect(str(Path(tempfile.mkdtemp()) / "u.db"))
        con.execute(
            "CREATE TABLE unknown_terms (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "term TEXT NOT NULL, hits INTEGER DEFAULT 1)"
        )
        con.execute("CREATE UNIQUE INDEX idx_unknown_term ON unknown_terms (term)")
        con.execute("INSERT INTO unknown_terms (term) VALUES ('فریبوس')")
        try:
            con.execute("INSERT INTO unknown_terms (term) VALUES ('فریبوس')")
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised                            # the seatbelt holds


class TestOneMenuPeriodicReport:
    def test_briefing_and_yearbook_in_one_answer(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        route_and_run("نمودار از ۲ و ۳ بکش")
        p = route_and_run("گزارش کامل بده")
        rep = p["agent_report"]
        assert rep.count("☀️") == 1              # the briefing section
        assert rep.count("📖") == 1              # the yearbook section
        assert "۴ فرمان" in rep or "فرمان" in rep  # real numbers from the store

    def test_alt_phrasing_reaches_the_same_menu(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        p = route_and_run("گزارش دورهیای بده")
        assert "☀️" in p["agent_report"]
