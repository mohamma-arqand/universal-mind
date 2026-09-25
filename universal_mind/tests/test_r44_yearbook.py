"""Tests: R44 item 16 — the yearbook (the platform narrates its own year).

Live laws:
1. Every number in the narrative is DERIVED from the real store — a seeded
   year's runs/lessons/verdicts appear in the PDF's own sentences.
2. An empty year is an honest first page, never a fabricated narrative.
3. A real PDF lands on disk (verifiable bytes).
4. The operator's question through the real router produces the yearbook.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any


def _seeded_store(tmp_path: Path, year: int) -> Any:
    """An isolated store with real runs, one lesson, and one human verdict."""
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(tmp_path / "year.db"))
    RunHistory(db)
    conn = sqlite3.connect(str(tmp_path / "year.db"))
    now = dt.datetime.now()
    for back, ok in ((0, 1), (0, 1), (1, 0)):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
            f"VALUES ('c{back}', 'data', {ok}, 0.9, '{ts}')"
        )
    conn.commit()
    conn.close()
    from universal_mind.planner_learning import _ensure_table

    _ensure_table(db)
    db.insert_many("planner_lessons", [
        {"capability": "chart", "operation": "bar", "excellence": "0.9500",
         "created_at": f"{year}-06-01 10:00:00"},
    ])
    db.execute(
        "CREATE TABLE IF NOT EXISTS operator_verdicts "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, verdict TEXT, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    db.insert_many("operator_verdicts", [
        {"run_id": "1", "verdict": "great", "created_at": f"{year}-06-02 10:00:00"},
        {"run_id": "2", "verdict": "bad", "created_at": f"{year}-06-03 10:00:00"},
    ])
    return db


class TestTheNarrative:
    def test_real_numbers_really_appear(self, tmp_path: Path) -> None:
        from universal_mind.yearbook import yearbook_sections

        db = _seeded_store(tmp_path, dt.date.today().year)
        data = yearbook_sections(dt.date.today().year, db=db)
        assert data["runs"] == 3, data
        assert data["ok_runs"] == 2
        assert data["lessons"] and data["lessons"][0][0] == "chart"
        assert data["verdicts"] == {"great": 1, "bad": 1}

    def test_an_empty_year_is_an_honest_first_page(self, tmp_path: Path) -> None:
        from universal_mind.yearbook import build_yearbook, yearbook_sections

        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(str(tmp_path / "empty.db"))
        RunHistory(db)
        data = yearbook_sections(1998, db=db)
        assert data["runs"] == 0
        r = build_yearbook(1998, db=db, out_dir=str(tmp_path))
        assert r["ok"] is True
        assert any("آغاز" in s for s in r["sections"]), r["sections"]
        assert not any("فرمان اجرا کردم" in s for s in r["sections"])

    def test_a_real_pdf_lands_on_disk(self, tmp_path: Path) -> None:
        from universal_mind.yearbook import build_yearbook

        db = _seeded_store(tmp_path, dt.date.today().year)
        r = build_yearbook(dt.date.today().year, db=db, out_dir=str(tmp_path))
        assert r["ok"] is True
        path = Path(r["path"])
        assert path.exists() and path.stat().st_size > 500
        assert path.read_bytes()[:4] == b"%PDF"

    def test_the_verdicts_reach_the_sentences(self, tmp_path: Path) -> None:
        from universal_mind.yearbook import build_yearbook

        db = _seeded_store(tmp_path, dt.date.today().year)
        r = build_yearbook(dt.date.today().year, db=db, out_dir=str(tmp_path))
        joined = " ".join(r["sections"])
        assert "عالی بود" in joined and "بد بود" in joined, joined


class TestTheQuestion:
    def test_the_operator_command_builds_the_yearbook(self, tmp_path: Path) -> None:
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        db = _seeded_store(tmp_path, dt.date.today().year)
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            p: Any = route_and_run("سالنامهام را بساز")
        assert p["ok"] is True
        assert p["route"] == ["pdf"], p["route"]
        pdf = p["result"]["pdf"]
        assert pdf["bytes"] > 500
        assert Path(pdf["path"]).read_bytes()[:4] == b"%PDF"
