"""Tests for history analytics — real statistics over real recorded runs."""

from __future__ import annotations

import pytest

import uuid

from universal_mind.history_analytics import (
    analytics_report,
    analyze_history,
)
from universal_mind.run_history import RunHistory


def _isolated_history() -> RunHistory:
    from universal_mind.database_suite import DatabaseSuite

    return RunHistory(DatabaseSuite())


class TestAnalytics:
    def test_empty_history_is_honest(self) -> None:
        stats = analyze_history(_isolated_history())
        assert stats.total_runs == 0
        assert analytics_report(stats) == "هنوز اجرایی ثبت نشده است."

    def test_counts_real_runs(self) -> None:
        history = _isolated_history()
        history.record("میانگین", ["data"], True)
        history.record("نمودار", ["chart"], True)
        history.record("شکست", ["data"], False)
        stats = analyze_history(history)
        assert stats.total_runs == 3
        assert stats.successful_runs == 2
        assert stats.failed_runs == 1
        assert abs(stats.success_rate - 2 / 3) < 1e-9

    def test_top_chains_and_capabilities(self) -> None:
        history = _isolated_history()
        marker = uuid.uuid4().hex[:6]
        history.record(f"a {marker}", ["data", "chart"], True)
        history.record(f"b {marker}", ["data", "chart"], True)
        history.record(f"c {marker}", ["data"], True)
        stats = analyze_history(history)
        assert stats.top_chains[0][0] == "data → chart"
        assert stats.top_chains[0][1] == 2
        assert stats.top_capabilities[0][0] == "data"
        assert stats.top_capabilities[0][1] == 3

    def test_per_capability_success(self) -> None:
        history = _isolated_history()
        history.record("x", ["data"], True)
        history.record("y", ["data"], False)
        stats = analyze_history(history)
        assert abs(stats.per_capability_success["data"] - 0.5) < 1e-9

    def test_report_renders_fluent_persian(self) -> None:
        history = _isolated_history()
        history.record("میانگین و نمودار", ["data", "chart"], True)
        stats = analyze_history(history)
        report = analytics_report(stats)
        assert "مجموع اجراها" in report
        assert "نرخ موفقیت" in report
        assert "پرکاربردترین زنجیرهها" in report
        assert "٪" in report
        # Persian digits are rendered (no raw ASCII numbers in the report).
        assert "1" not in report or "۱" in report

    def test_mean_excellence_computed_over_judged_runs(self) -> None:
        history = _isolated_history()
        history.record("a", ["data"], True, excellence=1.0)
        history.record("b", ["data"], True, excellence=0.5)
        history.record("c", ["data"], False, excellence=0.0)
        stats = analyze_history(history)
        # mean over SUCCESSFUL judged runs only: (1.0 + 0.5) / 2
        assert abs(stats.mean_excellence - 0.75) < 1e-9

    def test_old_rows_without_excellence_are_tolerated(self) -> None:
        history = _isolated_history()
        history.record("legacy", ["data"], True)  # no excellence (old shape)
        stats = analyze_history(history)
        assert stats.mean_excellence == 0.0  # honest: nothing judged yet
        assert stats.total_runs == 1

    @pytest.mark.live_store  # type: ignore[untyped-decorator]

    def test_end_to_end_real_history_has_content(self) -> None:
        """The operator's REAL persistent history (non-empty from real runs)."""
        stats = analyze_history()  # the real persistent db
        assert stats.total_runs > 0
        assert stats.success_rate > 0.5  # real runs overwhelmingly succeed
        report = analytics_report(stats)
        assert "نرخ موفقیت" in report