"""Tests: the tick notification + the memory-to-report flow."""

from __future__ import annotations


class TestTickNotification:
    def test_tick_with_fires_sends_the_honest_toast(self) -> None:
        """A tick that fired schedules reports them via a REAL Windows toast —
        Persian digits, successes first, failures named."""
        import sys
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        with mock_patch.object(sched_mod, "_store", lambda: suite),              mock_patch("universal_mind.real_notify.NotifyTool.notify") as toast:
            sched_mod.register("هر ۱۵ دقیقه میانگین ۲ و ۴ را حساب کن")
            result = tick()
        assert result["count"] >= 1
        assert toast.call_count >= 1  # the tick's summary toast was really sent
        body = toast.call_args.kwargs.get("body", "") or str(toast.call_args.args[-1])
        assert "کارِ زمان‌بندی‌شده" in body
        assert any(ch in body for ch in "۰۱۲۳۴۵۶۷۸۹")  # Persian digits in the toast

    def test_tick_without_fires_is_silent(self) -> None:
        """Nothing due → no toast (silence is honest when nothing ran)."""
        import sys
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        import universal_mind.scheduler as sched_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        import universal_mind.agent_loop as agent_mod

        _real_db = DatabaseSuite  # grabbed BEFORE the class-lambda patch
        _conn_calls: list[str] = []
        import importlib

        _dw = importlib.import_module("universal_mind.disk_watch")
        _wl = importlib.import_module("universal_mind.weekly_letter")
        _dbf = importlib.import_module("universal_mind.daily_briefing")
        with mock_patch.object(sched_mod, "_store", lambda: suite), \
             mock_patch.object(agent_mod, "_store", lambda: suite), \
             mock_patch.object(_dw, "DatabaseSuite", suite), \
             mock_patch.object(_wl, "DatabaseSuite", suite), \
             mock_patch.object(_dbf, "DatabaseSuite", suite), \
             mock_patch("universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite), mock_patch.object(_real_db, "shared_persistent", classmethod(lambda cls: suite)), \
             mock_patch("universal_mind.real_notify.NotifyTool.notify"), \
             mock_patch("universal_mind.notify_adapter.NotifyToolConnector") as connector:
            # fire everything once, then nothing is due (goals store also empty
            # — stopped goals in the LIVE store would rightly toast too).
            # R46 re-pin: the FIRST tick of a fresh day also writes the morning
            # briefing and (ISO-week boundary) the weekly letter through the
            # NotifyToolConnector — REAL work, not noise. The SECOND tick with
            # everything already written must not toast again.
            connector.return_value.connect.side_effect = (
                lambda params, kw: _conn_calls.append(kw.get("title", "?"))
            )
            tick()
            first_tick_conn = len(_conn_calls)
            tick()
            # R46: the FIRST tick of a fresh day writes the morning briefing
            # (and at an ISO-week boundary the weekly letter) through the
            # NotifyToolConnector — REAL work. The SECOND tick, with
            # everything already written, adds NOTHING (silence stays
            # honest when nothing ran).
            assert len(_conn_calls) == first_tick_conn


class TestMemoryToReportFlow:
    def test_the_memory_becomes_a_document(self) -> None:
        """«گزارش از ذخیرهشدهها را بساز» — the persistent store rendered as
        a real Persian pdf with the stored rows inside."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("گزارش از ذخیرهشدهها را بساز")
        # the planner puts the memory read FIRST (database is a sink that
        # feeds the report flow — the lock-step order this chain needs)
        assert payload["route"] == ["database", "pdf"]
        assert payload["ok"] is True
        flows = payload["flows"]
        assert any("حافظه → گزارش" in f for f in flows)
        assert payload["result"]["pdf"]["bytes"] > 30000  # a real table inside

    def test_the_readback_params_target_the_persistent_store(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("گزارش از ذخیرهشدهها را بساز", "database")
        assert params["operation"] == "query"
        assert params["persistent"] is True
        assert "chain_results" in params["sql"]
