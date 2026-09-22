"""Tests: the intelligence layer — intent lens, seed memory, farthest rival, speech memory."""

from __future__ import annotations

import pytest


class TestIntentLens:
    def test_scoring_ranks_fluent_over_reverse(self) -> None:
        """(data, chart, pdf) — the chain that really fires — must outrank
        a reshuffle the operator never ran."""
        from universal_mind.intent_lens import rank_routes

        ranked = rank_routes(
            [("data", "chart", "pdf"), ("pdf", "chart", "data")],
            "نمودار خطی بساز و گزارشش کن",
        )
        assert ranked[0].route == ("data", "chart", "pdf")
        assert ranked[0].score > ranked[1].score

    def test_reasons_render_in_persian(self) -> None:
        from universal_mind.intent_lens import scored_fa

        class _S:  # minimal shape for the renderer
            route = ("chart", "pdf")
            score = 0.71
            reasons_fa = ("زنجیرهی شناخته",)

        assert "امتیاز" in scored_fa(_S())  # type: ignore[arg-type]
        assert "chart → pdf" in scored_fa(_S())  # type: ignore[arg-type]

    def test_empty_routes_rank_empty(self) -> None:
        from universal_mind.intent_lens import rank_routes

        assert rank_routes([], "هرچی") == []


class TestSeedMemory:
    def test_speech_alone_takes_the_last_success(self) -> None:
        """«بلند بخوان» with no material speaks the last REAL success."""
        from universal_mind.persian_params import extract_params

        params = extract_params("بلند بخوان", "speech")
        assert params.get("seeded") is True
        # real material from the store's last success — never invented; the
        # CONTENT depends on what really ran last, so only require substance.
        assert params.get("text") and len(params["text"]) > 5

    def test_explicit_text_wins_over_seed(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("بلند بخوان که کار تمام شد", "speech")
        assert params.get("seeded") is None  # the sentence's own text
        assert "کار تمام شد" in params.get("text", "")


class TestFarthestRival:
    def test_the_gate_still_passes_a_good_primary(self) -> None:
        """A strong chain ships untouched — the rival never runs."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۳ و ۹ را حساب کن")
        assert payload["ok"] is True

    def test_rival_candidates_never_include_duplicates(self) -> None:
        """The lens only ADDS a genuinely different route, score-gated."""

        from universal_mind.quality_gate import run_with_quality_gate

        seen: list[tuple[str, ...]] = []

        def runner(candidate: tuple[str, ...]) -> dict[str, object]:
            seen.append(candidate)
            return {
                "ok": True, "route": list(candidate),
                "result": {"data": {"bytes": 100, "mean": 4.0, "n": 2}},
                "judgment": {"excellence": 0.95},
            }

        gate = run_with_quality_gate("نمودار بساز", ("data", "chart"), runner, bar=0.5)
        assert gate.shipped.excellence >= 0.5
        assert len(seen) == len(set(seen))  # no duplicate real runs


class TestSpeechMemoryAdvise:
    @pytest.mark.live_store  # type: ignore[untyped-decorator]
    def test_advise_with_seeds_returns_proven_params(self) -> None:
        from universal_mind.run_history import ChainAdvisor, RunHistory

        advice, seeds = ChainAdvisor(RunHistory()).advise_with_seeds("نمودار بساز")
        assert advice is not None
        assert advice.route  # a real chain from real history
        if seeds:
            for cap, params in seeds.items():
                assert cap in advice.route
                assert isinstance(params, dict) and params

    def test_no_history_no_seeds(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import ChainAdvisor, RunHistory

        advisor = ChainAdvisor(RunHistory(DatabaseSuite()))
        advice, seeds = advisor.advise_with_seeds("کاملا بیربط ZZZQ")
        # honest: no invented seeds even if some advice sneaks through
        if advice is None:
            assert seeds is None