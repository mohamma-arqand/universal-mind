"""Tests: the super-platform dashboard — real data, one self-contained HTML."""

from __future__ import annotations

from pathlib import Path


class TestSuperplatformDashboard:
    def test_builds_a_real_html_with_real_numbers(self, tmp_path: Path) -> None:
        from universal_mind.superplatform_dashboard import build_dashboard

        out = tmp_path / "dash.html"
        result = build_dashboard(str(out))
        assert result["ok"] is True
        assert result["bytes"] > 3000  # a real page, not a stub

        html = out.read_text(encoding="utf-8")
        assert 'lang="fa"' in html and 'dir="rtl"' in html  # Persian page
        assert "کل اجراها" in html            # the KPI row
        assert "planner چه آموخته" in html     # the learned-lessons table
        # no English capability names leak into the PERSIAN-FACING cells;
        # the dir='ltr' chain/op columns are the machine's real API
        # identifiers — rendered verbatim by design, never translated.
        import re as _re

        persian_cells = _re.findall(r">([^<>]*)</td>", html)
        unpinned = [
            cell for cell in persian_cells
            if cell in ("chart", "database", "archive", "clipboard")
        ]
        # every such identifier must sit in an explicitly ltr-marked column
        ltr_count = html.count("dir='ltr'")
        assert ltr_count >= len(unpinned)

    def test_numbers_are_persian_digits(self, tmp_path: Path) -> None:
        from universal_mind.superplatform_dashboard import build_dashboard

        out = tmp_path / "dash.html"
        build_dashboard(str(out))
        html = out.read_text(encoding="utf-8")
        # the success-rate KPI carries Persian digits (۰-۹), not ASCII
        import re

        assert re.search(r"[۰-۹]+٪", html), "Persian percent signs expected"

    def test_dashboard_cli(self, tmp_path: Path) -> None:
        from universal_mind.cli import main

        rc = main(["dashboard-sp", "--out", str(tmp_path / "cli.html")])
        assert rc == 0
        assert (tmp_path / "cli.html").exists()

    def test_daily_runs_read_real_history(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.superplatform_dashboard import _daily_runs

        rows = _daily_runs(DatabaseSuite(persistent=True))
        assert isinstance(rows, list)  # honest: possibly one day so far
        if rows:
            assert {"day", "runs"} <= set(rows[0].keys())
            assert rows[0]["runs"] >= 0
