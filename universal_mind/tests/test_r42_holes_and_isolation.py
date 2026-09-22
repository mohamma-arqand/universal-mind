"""Tests: R42 — the navigation holes closed + store isolation.

Every hole found by the live everyday-command sweep («نشناختم» answers)
now has a real answer; and tests read an ISOLATED store, never the
operator's (the conftest autouse fixture).
"""

from __future__ import annotations


def _seed_run(command: str, route: list[str], ok: bool = True) -> None:
    """Seed the ISOLATED store with one real recorded run."""
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory

    RunHistory(DatabaseSuite.shared_persistent()).record(
        command, route, ok, excellence=1.0 if ok else 0.0
    )


class TestNavigationHolesClosed:
    """The 8 holes the sweep found — each answers, never «نشناختم»."""

    def test_help_variants_list_capabilities(self) -> None:
        from universal_mind.persian_router import route_and_run

        for phrase in ("چی بلدی؟", "قابلیتهات رو نشون بده"):
            p = route_and_run(phrase)
            assert "نشناختم" not in p["agent_report"], phrase
            assert "قابلیت" in p["agent_report"], phrase
        # the help-me-choose variant answers with examples (conversational).
        p = route_and_run("کمک کن چی کار کنم؟")
        assert "نشناختم" not in p["agent_report"]
        assert "نمودار" in p["agent_report"]  # real example commands

    def test_farewell_gets_a_warm_answer(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("خدانگهدار")
        assert p["route"] == ["conversational"]
        assert "منتظر" in p["agent_report"]

    def test_today_work_counts_real_runs(self) -> None:
        from universal_mind.persian_router import route_and_run

        _seed_run("کار امروز", ["data"])
        p = route_and_run("امروز چی کار کردی؟")
        assert "فرمان اجرا کردم" in p["agent_report"]
        assert "۱" in p["agent_report"]  # the seeded run, counted

    def test_today_with_no_work_is_honest(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("امروز چی کار کردی؟")
        assert "اولین فرمان" in p["agent_report"]

    def test_files_today_lists_recent_successes(self) -> None:
        from universal_mind.persian_router import route_and_run

        _seed_run("گزارش فروش", ["pdf"])
        p = route_and_run("فایلهای ساختهشده امروز")
        assert "گزارش فروش" in p["agent_report"]

    def test_memory_speaks_lessons(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        db = DatabaseSuite.shared_persistent()
        db.execute(
            "CREATE TABLE IF NOT EXISTS planner_lessons "
            "(id INTEGER PRIMARY KEY, capability TEXT, operation TEXT, "
            "excellence REAL, created_at TEXT)"
        )
        db.execute(
            "INSERT INTO planner_lessons (capability, operation, excellence, created_at) "
            "VALUES ('chart', 'line', 1.0, datetime('now', 'localtime'))"
        )
        p = route_and_run("حافظهات چی میگن؟")
        assert "درس" in p["agent_report"]
        assert "line" in p["agent_report"]

    def test_learning_question_answers(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چی یاد گرفتی؟")
        assert "نشناختم" not in p["agent_report"]
        assert ("درس" in p["agent_report"]) or ("یاد نگرفتهام" in p["agent_report"])


class TestStoreIsolation:
    """A test's writes land in the ISOLATED store, never the operator's."""

    def test_route_and_run_never_touches_the_live_store(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        live = DatabaseSuite(persistent=True)
        before = live.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
        route_and_run("میانگین ۲ و ۸ را حساب کن")
        after = live.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
        assert after == before  # the run went to the isolated temp store

    def test_fixture_store_is_not_the_live_one(self) -> None:
        from universal_mind.database_suite import DatabaseSuite

        shared = DatabaseSuite.shared_persistent()
        live = DatabaseSuite(persistent=True)
        assert str(shared.db_path) != str(live.db_path)
