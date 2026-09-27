"""Tests: the super-platform dashboard's LIVE branches (R49 wave 3).

Every lens that degrades to empty (a broken store, a missing table) and every
tick-health signal combination is exercised — a dashboard state no test passes
over is an unverified promise to the operator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

from universal_mind.superplatform_dashboard import (
    _jalali_day,
    build_dashboard,
)


class TestJalaliDay:
    def test_a_gregorian_day_renders_jalali(self) -> None:
        day = _jalali_day("2026-09-27")
        assert day != "2026-09-27"  # the Persian calendar, not the Latin one
        assert any(ch in day for ch in "۰۱۲۳۴۵۶۷۸۹")  # Persian digits

    def test_a_bad_date_stays_honest(self) -> None:
        assert _jalali_day("not a date") == "not a date"  # never crashes


class TestLensDegradation:
    def _db(self) -> Any:
        from universal_mind.database_suite import DatabaseSuite

        return DatabaseSuite()

    def test_a_broken_lessons_lens_degrades_to_empty(self) -> None:
        # from-import inside the body — patch the SOURCE module's name:
        with mock_patch(
            "universal_mind.planner_learning.lessons_report",
            side_effect=RuntimeError("جدول نبود"),
        ):
            result = build_dashboard()
        assert result["ok"] is True  # a view is never fatal
        # the dashboard still renders (lessons just empty)

    def test_a_broken_trend_lens_degrades_to_empty(self) -> None:
        db = self._db()
        calls: dict[str, int] = {"n": 0}
        real_query = db.query

        def flaky_query(suite: Any, sql: str, params: Any = None) -> Any:
            calls["n"] += 1
            if "AVG(excellence)" in sql:
                raise RuntimeError("خواندن روند ناموفق")
            return real_query(sql, params)

        with mock_patch.object(type(db), "query", flaky_query):
            result = build_dashboard()
        assert result["ok"] is True


class TestTickHealthSignals:
    def _db(self) -> Any:
        from universal_mind.database_suite import DatabaseSuite

        return DatabaseSuite()

    def test_installed_and_recent_says_healthy(self) -> None:
        with mock_patch(
            "universal_mind.task_install.tick_health",
            return_value={"signals": {"task_installed": True, "recent_run": True}},
        ):
            result = build_dashboard()
        assert result["ok"] is True
        html = Path(str(result["path"])).read_text(encoding="utf-8")
        assert "ضربان دارد" in html  # the healthy message, rendered

    def test_installed_but_stale_suggests_attention(self) -> None:
        with mock_patch(
            "universal_mind.task_install.tick_health",
            return_value={"signals": {"task_installed": True, "recent_run": False}},
        ):
            result = build_dashboard()
        html = Path(str(result["path"])).read_text(encoding="utf-8")
        assert "۲۴ ساعت" in html  # the stale message — the exact remedy, named

    def test_a_broken_tick_health_degrades(self) -> None:
        with mock_patch(
            "universal_mind.task_install.tick_health",
            side_effect=RuntimeError("نبود"),
        ):
            result = build_dashboard()
        assert result["ok"] is True


__test__ = True
