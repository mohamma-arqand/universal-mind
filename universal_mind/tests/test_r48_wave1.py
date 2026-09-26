"""R48 wave 1 — the strict judge: evidence-earned virtue, no rubber stamps.

Item 1: COURAGE demands an inspectable witness (real path / non-zero bytes /
a concrete number); a bare {"ok": True} is half-courage, never full.
Item 2: TEMPERANCE learns each route's own median (>=3 real witnesses,
3x band); without witnesses the 60s global ceiling stands.
Item 3: WISDOM counts a shape-correct-but-empty result as half-served.
Item 4: the old binary-temperance test is re-pinned to the proportional law.
"""

from __future__ import annotations

import json as J
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.arete.run_judgment import run_virtue_scores
from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _db(rows: list[dict[str, Any]] | None = None) -> DatabaseSuite:
    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r48w1.db"))
    RunHistory(suite)
    if rows:
        suite.insert_many("run_history", rows)
    return suite


_BASE = {"route": ["chart"], "errors": {}}


class TestStrictCourage:
    def test_bare_ok_is_half_courage_never_full(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True,
                                    "result": {"chart": {"ok": True}}})
        assert scores["courage"] == 0.5  # shape right, substance absent

    def test_a_real_path_is_full_courage(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True, "result": {
            "chart": {"ok": True, "path": "line.png"}}})
        assert scores["courage"] == 1.0

    def test_a_concrete_number_is_full_courage(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True, "result": {
            "chart": {"ok": True, "mean": 12.5}}})
        assert scores["courage"] == 1.0

    def test_nonzero_bytes_is_full_courage(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True, "result": {
            "chart": {"ok": True, "bytes": 2048}}})
        assert scores["courage"] == 1.0

    def test_explicit_failure_is_zero_courage(self) -> None:
        scores = run_virtue_scores({**_BASE, "result": {
            "chart": {"ok": False, "error": "شکست"}}})
        assert scores["courage"] == 0.0


class TestLearnedTemperance:
    def test_witnesses_tighten_the_band(self) -> None:
        db = _db([
            {"command": "w", "route": "chart", "succeeded": 1,
             "excellence": 0.9, "durations_ms": J.dumps({"chart": 100.0})}
            for _ in range(4)
        ])
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            fast = run_virtue_scores({**_BASE, "result": {
                "chart": {"path": "x.png"}},
                "durations_ms": {"chart": 250.0}})   # 2.5x median: inside
            slow = run_virtue_scores({**_BASE, "result": {
                "chart": {"path": "x.png"}},
                "durations_ms": {"chart": 5_000.0}})  # 50x median: outside
        assert fast["temperance"] == 1.0
        assert slow["temperance"] < 0.1

    def test_no_witnesses_keep_the_global_ceiling(self) -> None:
        db = _db()
        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: db)):
            ok = run_virtue_scores({**_BASE, "result": {
                "chart": {"path": "x.png"}},
                "durations_ms": {"chart": 30_000.0}})   # under 60s
            over = run_virtue_scores({**_BASE, "result": {
                "chart": {"path": "x.png"}},
                "durations_ms": {"chart": 120_000.0}})  # over 60s
        assert ok["temperance"] == 1.0
        assert over["temperance"] == 0.5  # 60s/120s: proportional wound

    def test_durations_persist_through_record(self) -> None:
        """The router's real durations must survive into run_history."""
        suite = _db()
        hist = RunHistory(suite)
        hist.record("آزمون", ["chart"], True, excellence=0.9,
                    durations_ms={"chart": 123.4})
        q = suite.query("SELECT durations_ms FROM run_history")
        assert q["rows"][0]["durations_ms"]
        data = J.loads(q["rows"][0]["durations_ms"])
        assert data == {"chart": 123.4}


class TestWisdomDepth:
    def test_empty_dict_is_half_served(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True,
                                    "result": {"chart": {"ok": True}}})
        assert scores["wisdom"] == 0.5

    def test_substantive_result_is_fully_served(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True, "result": {
            "chart": {"ok": True, "mean": 3.0}}})
        assert scores["wisdom"] == 1.0

    def test_errors_cap_wisdom_at_half(self) -> None:
        scores = run_virtue_scores({**_BASE, "ok": True, "result": {
            "chart": {"mean": 3.0}},
            "errors": {"chart": "بعد از ساخت خراب شد"}})
        assert scores["wisdom"] <= 0.5
