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
        assert scores["temperance"] == 0.0

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

        payload = route_and_run("نمودار خطی بساز و گزارشش کن")
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