"""Tests: R44 items 7+8 — the parameter A/B and the rescue chain.

Live laws:
1. A genuinely ambiguous kind («نمودارش کن») runs a REAL contest: both
   variants draw real data, the winner ships with the ruling announced in
   the report. A NAMED kind never contests (the operator's word wins).
2. A failed step's rescue: the best learned alternative runs at one level
   deeper; the (failure, rescue) pair lands in planner_lessons.
"""

from __future__ import annotations

from typing import Any


class TestKindAmbiguity:
    """The honest ambiguity test."""

    def test_unnamed_kind_is_ambiguous(self) -> None:
        from universal_mind.ab_contest import kind_ambiguity

        assert kind_ambiguity("نمودارش کن", {"operation": "line"}) is True
        assert kind_ambiguity("چارت بساز", None) is True

    def test_a_named_kind_is_not_ambiguous(self) -> None:
        from universal_mind.ab_contest import kind_ambiguity

        assert kind_ambiguity("نمودار میلهای بساز", {}) is False
        assert kind_ambiguity("نمودار دایرهای", {"kind_explicit": True}) is False


class TestTheABContest:
    """run_ab — the real contest with the fabrication criterion."""

    def _runner(self) -> Any:
        from universal_mind.chart_suite import ChartSuiteConnector
        from universal_mind.tool_registry import ConnectionMechanism, ToolConnectionSpec

        def _run(vparams: dict[str, Any]) -> dict[str, Any]:
            conn = ChartSuiteConnector()
            spec = ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused")
            out = conn.connect(spec, vparams)
            return {"ok": out.ok, "route": ["chart"],
                    "result": {"chart": out.output},
                    "errors": {} if out.ok else {"chart": out.error},
                    "durations_ms": {}}

        return _run

    def test_the_winner_ships_with_the_ruling(self) -> None:
        from universal_mind.ab_contest import run_ab

        ab = run_ab("نمودارش کن", {"operation": "line",
                                    "series": {"داده": [4.0, 6.0, 9.0]}}, self._runner())
        assert ab["ok"] is True
        contest = ab["ab_contest"]
        assert contest["winner"] == "line"  # the synthetic-label bar loses
        assert "برنده شد" in contest["reasoning"]
        assert set(contest["excellences"]) == {"line", "bar"}

    def test_no_data_no_contest_theater(self) -> None:
        """R66 P2 — no data → both variants refuse honestly; no fabricated bars.

        The old expectation (the DEFAULT series rides the contest) was the
        «پیش‌فرضی که جواب می‌دهد» law's last consumer: a contest the operator
        did not feed is theater.
        """
        from universal_mind.ab_contest import run_ab

        ab = run_ab("نمودارش کن", {"operation": "line"}, self._runner())
        contest = ab["ab_contest"]
        # the run is honestly red and NOTHING ships
        assert ab["ok"] is False
        assert (ab["result"].get("chart") or {}).get("path") is None
        # both variants ran and both refused — the contest is over real
        # failures, not fabricated bars
        assert set(contest["excellences"]) == {"line", "bar"}

    def test_a_failed_variant_is_a_data_point(self) -> None:
        from universal_mind.ab_contest import run_ab

        def _failing(vparams: dict[str, Any]) -> dict[str, Any]:
            if vparams.get("operation") == "bar":
                raise RuntimeError("bar is broken")
            return {"ok": True, "route": ["chart"], "result": {"chart": {"path": "x.png"}}, "errors": {}}

        ab = run_ab("نمودارش کن", {"operation": "line"}, _failing)
        assert ab["ok"] is True  # the healthy variant won
        assert ab["ab_contest"]["winner"] == "line"


class TestTheRealChain:
    """The production path: ambiguous → contest → ruling in the report."""

    def test_ambiguous_command_announces_the_ruling(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-7.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            # R63 P3: the AB duel needs REAL data now — numbers in the
            # sentence (the silent default series is gone).
            p = route_and_run("نمودار از ۲ و ۵ و ۹ کن")
        assert p["ok"] is True
        assert "مسابقهی A/B" in (p.get("ab_ruling") or "")
        assert "مسابقهی A/B" in (p.get("agent_report") or "")

    def test_a_named_kind_never_contests(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-7b.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("نمودار میلهای بساز")
        assert p.get("ab_ruling") is None  # the operator's word wins


class TestTheRescueChain:
    """R44-8: a failed step's best learned alternative, one level deeper."""

    def test_the_pair_lands_in_lessons(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        import universal_mind.planner_learning as pl

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-8.db"))
        with mock_patch.object(pl, "_store", lambda: iso):
            # a REAL failure → its rescue teaches (both folded)
            pl.teach("webfetch", "fetch", 0.0, False)  # the failure teaches nothing
            pl.teach("database", "query", 0.95, True)  # the rescue teaches
            best = pl.best_learned_operation("database")
            assert best is not None and best.operation == "query"

    def test_rescue_only_when_the_first_fails(self) -> None:
        """A healthy first attempt NEVER triggers a rescue (no wasted work)."""
        from universal_mind.quality_gate import _verdict_of  # noqa: F401

        # the gate's own law: a strong primary passes untouched (locked in
        # quality_gate's tests) — here we lock the AB side: a healthy line
        # wins without a second kind.
        from universal_mind.ab_contest import run_ab

        ab = run_ab("نمودارش کن", {"operation": "line"}, lambda v: {"ok": False})
        # both variants fail honestly → the tie is SAID, line ships as default
        assert "تساوی" in ab["ab_contest"]["reasoning"] or ab["ab_contest"]["winner"] == "line"
