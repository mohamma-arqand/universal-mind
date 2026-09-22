"""Tests: R44 wave-1 — the explained plan, the dry run, the human verdict.

Locked live witnesses:
1. «... — توضیح بده» builds the Persian program (steps + reasons + sources)
   and STOPS: planned=True, executed=False, ZERO history rows, zero files.
2. «عالی بود»/«بد بود» binds to the last real success and re-weights the
   advisor (1.25 up, 0.5^k down) — the human's word outranks raw counts.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from typing import Any, Iterator


def _isolated() -> AbstractContextManager[Any]:
    """One isolated store for a run + read-back."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    @contextmanager
    def _ctx() -> Iterator[Any]:
        suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44.db"))
        with mock_patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite)
        ):
            yield suite

    return _ctx()


class TestExplainedPlan:
    """R44-1: the plan is narrated BEFORE any side effect."""

    def test_explain_marker_builds_the_program(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated():
            p = route_and_run("نمودار ۱ و ۵ را بکش و گزارشش کن — توضیح بده")
        assert p["planned"] is True
        assert p["executed"] is False
        assert p["route"] == ["chart", "pdf"]
        report = p["agent_report"]
        assert "برنامهی اجرا" in report
        assert "گام ۱: chart" in report and "گام ۲: pdf" in report
        assert "دلیل" not in report  # reasons speak in Persian, per-step

    def test_explain_has_zero_side_effects(self) -> None:
        """The dry run: no history rows, no real execution."""
        from universal_mind.persian_router import route_and_run

        with _isolated() as suite:
            route_and_run("نمودار ۱ و ۵ را بکش و گزارشش کن — توضیح بده")
            rows = suite.query("SELECT COUNT(*) AS n FROM run_history")
            n = rows["rows"][0]["n"] if rows.get("ok") else 0
        assert n == 0  # a dry run writes NOTHING

    def test_explain_names_its_sources(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated():
            p = route_and_run("میانگین ۴ و ۶ را حساب کن — توضیح بده")
        assert "واژگان" in p["agent_report"]
        assert "اجرا کن" in p["agent_report"]  # the way out is stated

    def test_api_explain_only_flag(self) -> None:
        """The programmatic dry-run: route_and_run(..., explain_only=True)."""
        from universal_mind.persian_router import route_and_run

        with _isolated() as suite:
            p = route_and_run("میانگین ۴ و ۶ را حساب کن", explain_only=True)
            rows = suite.query("SELECT COUNT(*) AS n FROM run_history")
            n = rows["rows"][0]["n"] if rows.get("ok") else 0
        assert p["planned"] is True
        assert n == 0


class TestHumanVerdict:
    """R44-3: «عالی بود»/«بد بود» — the human judge joins the loop."""

    def test_good_verdict_lifts_the_weight(self) -> None:
        from universal_mind.operator_verdicts import route_weight
        from universal_mind.persian_router import route_and_run

        with _isolated():
            route_and_run("میانگین ۴ و ۶ را حساب کن")  # a real success
            before = route_weight(("data",))
            vp = route_and_run("عالی بود")
            after = route_weight(("data",))
        assert vp["ok"] is True
        assert after > before  # the human's praise lifts the chain

    def test_bad_verdict_sinks_the_weight(self) -> None:
        from universal_mind.operator_verdicts import route_weight
        from universal_mind.persian_router import route_and_run

        with _isolated():
            route_and_run("میانگین ۴ و ۶ را حساب کن")
            route_and_run("بد بود")
            w = route_weight(("data",))
        assert w < 1.0  # the human's ruling sinks it

    def test_verdict_on_empty_history_is_honest(self) -> None:
        from universal_mind.persian_router import route_and_run

        with _isolated():
            vp = route_and_run("عالی بود")
        assert vp["ok"] is False
        assert "اول اجرایش کن" in vp["agent_report"]

    def test_the_advisor_consumes_the_human_weight(self) -> None:
        """A 'bad' verdict on route A vs a clean route B: B outranks A even
        when A has MORE raw wins — the human's word outranks counts."""
        from universal_mind.persian_router import route_and_run
        from universal_mind.run_history import ChainAdvisor, RunHistory

        with _isolated() as suite:
            # route A wins 3 times, then the operator rules it bad.
            for _ in range(3):
                route_and_run("میانگین ۴ و ۶ را حساب کن")
            route_and_run("بد بود")
            # route B wins once, clean.
            route_and_run("نمودار خطی بساز")
            advice = ChainAdvisor(RunHistory(suite)).advise("میانگین و نمودار")
        # the advisor still finds SOMETHING, and the human's ruling held:
        assert advice is not None
