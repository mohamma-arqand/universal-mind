"""Tests: ARETĒ virtue-judgment over REAL super-platform runs."""

from __future__ import annotations

from universal_mind.arete.run_judgment import judge_run, run_virtue_scores


class TestVirtueScoresFromRealData:
    def test_perfect_run_scores_full_excellence(self) -> None:
        run = {
            "route": ["chart", "pdf"],
            "result": {"chart": {"path": "x.png", "bytes": 500}, "pdf": {"path": "y.pdf", "bytes": 5000}},
            "durations_ms": {"chart": 10.0, "pdf": 20.0},
            "errors": {},
        }
        scores = run_virtue_scores(run)
        assert scores == {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 1.0}
        verdict = judge_run(run)
        assert verdict["excellence"] == 1.0
        assert verdict["disqualified"] is False

    def test_missing_capability_wounds_wisdom(self) -> None:
        run = {
            "route": ["chart", "pdf"],
            "result": {"chart": {"path": "x.png", "bytes": 500}},  # pdf produced nothing
            "durations_ms": {"chart": 10.0},
            "errors": {},
        }
        scores = run_virtue_scores(run)
        assert scores["wisdom"] == 0.5
        # pdf appears NOWHERE (neither result nor error) → justice wounded too:
        # the platform dropped it silently, which is precisely what justice polices.
        assert scores["justice"] == 0.5

    def test_unbounded_duration_wounds_temperance(self) -> None:
        run = {
            "route": ["media"],
            "result": {"media": {"path": "x.mp4", "bytes": 100}},
            "durations_ms": {"media": 120_000.0},  # 2 minutes: intemperate
            "errors": {},
        }
        scores = run_virtue_scores(run)
        # R48-2 re-pin: temperance is now PROPORTIONAL (ceiling/duration),
        # not binary. 120s against the 60s global ceiling (no learned
        # witnesses) → exactly 0.5: wounded, never silently "temperate".
        assert scores["temperance"] == 0.5

    def test_learned_median_tightens_the_band(self) -> None:
        """With >=3 real witnesses, a 3x-slower run is intemperate."""
        import json as J
        import tempfile
        from pathlib import Path as _P
        from unittest.mock import patch as _patch

        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(str(_P(tempfile.mkdtemp()) / "temper.db"))
        RunHistory(db)
        db.insert_many("run_history", [
            {"command": "w", "route": "media", "succeeded": 1,
             "excellence": 0.9,
             "durations_ms": J.dumps({"media": 100.0})}
            for _ in range(4)
        ])
        with _patch.object(DatabaseSuite, "shared_persistent",
                           classmethod(lambda cls: db)):
            fast = run_virtue_scores({
                "route": ["media"],
                "result": {"media": {"path": "x.mp4", "bytes": 1}},
                "durations_ms": {"media": 200.0},  # 2x median: inside 3x
                "errors": {},
            })
            slow = run_virtue_scores({
                "route": ["media"],
                "result": {"media": {"path": "x.mp4", "bytes": 1}},
                "durations_ms": {"media": 30_000.0},  # 300x median
                "errors": {},
            })
        assert fast["temperance"] == 1.0
        assert slow["temperance"] < 0.05  # the learned band bites

    def test_silently_dropped_capability_wounds_justice(self) -> None:
        run = {
            "route": ["chart", "pdf"],
            "result": {"chart": {"path": "x.png", "bytes": 500}},  # pdf nowhere at all
            "durations_ms": {"chart": 10.0},
            "errors": {},
        }
        scores = run_virtue_scores(run)
        assert scores["justice"] == 0.5  # one of two unaccounted

    def test_empty_route_is_zero_not_one(self) -> None:
        scores = run_virtue_scores({"route": [], "result": {}, "durations_ms": {}, "errors": {}})
        assert scores["wisdom"] == 0.0  # absence of work is NOT success


class TestRealRunJudged:
    def test_a_real_persian_run_is_judged(self) -> None:
        from universal_mind.persian_router import route_and_run

        # R63: real data in the sentence — the silent default series is gone.
        payload = route_and_run("نمودار خطی از ۲ و ۷ بساز و گزارشش کن")
        verdict = judge_run(payload)
        assert verdict["scores"]["wisdom"] == 1.0
        assert verdict["excellence"] >= 0.9
        assert verdict["disqualified"] is False
        assert "excellence" in verdict["reasoning"]

    def test_a_failed_run_is_disqualified(self) -> None:
        run = {
            "route": ["nonexistent"],
            "result": {},
            "durations_ms": {},
            "errors": {"nonexistent": "no tool can honor 'nonexistent'"},
        }
        verdict = judge_run(run)
        assert verdict["scores"]["wisdom"] == 0.0
        assert verdict["excellence"] < 1.0