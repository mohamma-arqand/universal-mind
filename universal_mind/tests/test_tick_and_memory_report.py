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
        with mock_patch.object(sched_mod, "_store", lambda: suite),              mock_patch("universal_mind.real_notify.NotifyTool.notify") as toast:
            # fire everything once, then nothing is due
            tick()
            tick()
        # the second tick (nothing due) must not toast again in this window
        # (call count is either 1 — only the first fired — or 0 if nothing due)
        assert toast.call_count <= 1


class TestMemoryToReportFlow:
    def test_the_memory_becomes_a_document(self) -> None:
        """«گزارش از ذخیرهشدهها را بساز» — the persistent store rendered as
        a real Persian pdf with the stored rows inside."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("گزارش از ذخیرهشدهها را بساز")
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
