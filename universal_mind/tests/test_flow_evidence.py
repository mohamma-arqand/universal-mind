"""Tests: the flow-evidence column + the compute→chart flow."""

from __future__ import annotations


class TestFlowEvidenceColumn:
    def test_migration_adds_the_flows_column(self) -> None:
        """A persistent DB without `flows` gains it in place."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite()
        RunHistory(db)
        cols = {
            str(r["name"])
            for r in db.query("SELECT name FROM pragma_table_info('run_history')")["rows"]
        }
        assert "flows" in cols

    def test_record_persists_flows(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite()
        RunHistory(db).record("تست", ["data"], True, flows=["data → chart (تست)"])
        row = db.query("SELECT flows FROM run_history ORDER BY id DESC LIMIT 1")["rows"][0]
        assert "→ chart" in row["flows"]

    def test_the_live_router_records_its_flows(self) -> None:
        """A real two-capability run leaves ITS OWN flows in the history.

        The query is anchored to THIS test's unique command — the live store
        keeps recording other runs' flows (conversational witnesses, later
        test files), and "the newest flows row" is whoever ran last, a
        history-snapshot bomb (the R51 crown lesson in a new coat)."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        marker = "میانگین ۳ و ۶ را حساب کن و نمودارش را بکش"
        route_and_run(marker)
        row = DatabaseSuite(persistent=True).query(
            "SELECT route, flows FROM run_history WHERE command = ? AND flows != '' "
            "ORDER BY id DESC LIMIT 1",
            (marker,),
        )["rows"]
        assert row and "→ chart" in row[0]["flows"]


class TestComputeToChartFlow:
    def test_the_computed_series_is_plotted(self) -> None:
        """«حساب کن و نمودارش را بکش» — the chart plots THE COMPUTED numbers."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۳ و ۶ را حساب کن و نمودارش را بکش")
        assert payload["ok"] is True
        assert any("→ chart" in f for f in payload["flows"])

    def test_metrics_from_a_stats_run_become_a_series(self) -> None:
        """A stats output (mean/min/max) alone becomes a real plotted series."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "chart", {"operation": "line"}, "data",
            {"mean": 4.5, "std": 1.5, "min": 3.0, "max": 6.0, "count": 2},
            "cmd", (), {},
        )
        assert desc is not None and "→ chart" in desc
        series = params["series"]["محاسبهشده"]
        # mean==median here (4.5) — the series de-duplicates its metrics
        assert sorted(series) == [3.0, 4.5, 6.0]

    def test_no_metrics_no_flow(self) -> None:
        """A producer with nothing numeric flows nothing (honest)."""
        from universal_mind.orchestration import _flow_params

        params, desc = _flow_params(
            "chart", {"operation": "line"}, "data", {"note": "بدون عدد"}, "cmd", (), {},
        )
        assert desc is None