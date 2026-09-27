"""Tests: R45 wave-2 — the dashboard's new houses and the weekly letter.

Live laws:
1. The dashboard renders the pulse house (streak + silent days, Jalali),
   the drift house (hot-path ratio vs the committed baseline), and the
   human-loop house (verdicts + red-team findings) from the REAL store.
2. The weekly letter is derived from real week rows (LOCAL-day law), is
   one row per ISO week, answers «گزارش هفته چطور بود؟», and a silent
   week is written as a silent week — never fabricated.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite


def _seeded(tmp_path: Path, *, with_week: bool = True) -> DatabaseSuite:
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(tmp_path / "w2.db"))
    RunHistory(db)
    now = dt.datetime.now()
    days = (0, 1, 2, 5) if with_week else (40, 41)
    oks = (1, 1, 0, 1) if with_week else (1, 1)
    for back, ok in zip(days, oks, strict=True):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('نمودار بکش','data',{ok},1.0,'','{ts}')"
        )
    return db


def _router(db: DatabaseSuite) -> Any:
    from universal_mind.persian_router import route_and_run

    def _run(cmd: str) -> dict[str, Any]:
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            return route_and_run(cmd)

    return _run


class TestDashboardHouses:
    def test_pulse_house_shows_streak_and_silent_days(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.superplatform_dashboard import build_dashboard

            r = build_dashboard(str(tmp_path / "d.html"))
        html = Path(str(r["path"])).read_text(encoding="utf-8")
        assert "تپش (۷ روز)" in html
        m = re.search(r"رشتهی تپش: ([^<]+)<", html)
        assert m and "روز پیوسته" in m.group(1)

    def test_drift_house_shows_the_ratio(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.superplatform_dashboard import build_dashboard

            r = build_dashboard(str(tmp_path / "d.html"))
        html = Path(str(r["path"])).read_text(encoding="utf-8")
        assert "رانش کارایی" in html
        assert re.search(r"\d+ms / مبنا", html)

    def test_human_house_counts_real_verdicts(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.operator_verdicts import record_verdict

            record_verdict("نمودار بکش", "good")
            record_verdict("نمودار بکش", "bad")
            from universal_mind.superplatform_dashboard import build_dashboard

            r = build_dashboard(str(tmp_path / "d.html"))
        html = Path(str(r["path"])).read_text(encoding="utf-8")
        m = re.search(r"رأیها: ([^<]+)", html)
        assert m and "۱ 👍" in m.group(1) and "۱ 👎" in m.group(1)


class TestWeeklyLetter:
    def test_letter_from_real_week(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.weekly_letter import week_letter

            info = week_letter(db=db)
        assert info["ok"] and info["runs"] == 4 and info["ok_runs"] == 3
        assert "۴ فرمان" in info["report"] and "۷۵٪" in info["report"]
        assert "پرکاربردترین مسیر" in info["report"]

    def test_silent_week_is_honest(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path, with_week=False)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.weekly_letter import week_letter

            info = week_letter(db=db)
        assert info["runs"] == 0
        assert "ساکت" in info["report"]

    def test_one_row_per_week_and_due_flips(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            from universal_mind.weekly_letter import (
                due_this_week,
                record_weekly_letter,
            )

            assert due_this_week(db=db) is True
            record_weekly_letter(db=db)
            assert due_this_week(db=db) is False

    def test_asked_letter_answers(self, tmp_path: Path) -> None:
        db = _seeded(tmp_path)
        run = _router(db)
        p = run("گزارش هفته چطور بود؟")
        assert p["route"] == ["reflexive"]
        assert "نامهی هفته" in p["agent_report"]
        assert "۴ فرمان" in p["agent_report"]
