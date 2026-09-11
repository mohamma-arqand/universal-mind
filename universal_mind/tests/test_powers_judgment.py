"""Direct tests for the Judgment power (InMemoryJudgment.judge).

Judgment is LIVE and vital (arbiter, standard, counterfactual, lineage all import
CandidateOutput/Verdict), but its scoring body was only indirectly exercised and
had a latent ZeroDivisionError on empty criteria. These tests cover every branch,
including the guard added for it.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from universal_mind.powers.judgment import (
    CandidateOutput,
    InMemoryJudgment,
    JudgmentInput,
    Verdict,
)


def _input(candidates: list[CandidateOutput], criteria: list[str] | None = None) -> JudgmentInput:
    return JudgmentInput(
        goal="summarize",
        success_criteria=criteria if criteria is not None else ["summary", "clear"],
        candidates=candidates,
        context={},
    )


def _cand(sid: str, output: object, metadata: dict[str, Any] | None = None) -> CandidateOutput:
    return CandidateOutput(strategy_id=sid, output=output, metadata=metadata or {})


def _run(j: JudgmentInput) -> Any:
    return asyncio.run(InMemoryJudgment().judge(j))


def test_empty_candidates_deny() -> None:
    out = _run(_input([]))
    assert out.verdict is Verdict.DENY
    assert out.chosen_strategy_id is None
    assert out.scores == {}


def test_empty_criteria_defers_instead_of_crashing() -> None:
    # Regression: empty success_criteria used to raise ZeroDivisionError.
    out = _run(_input([_cand("a", "some output")], criteria=[]))
    assert out.verdict is Verdict.DEFER
    assert out.chosen_strategy_id is None
    assert out.scores == {"a": 0.0}


def test_full_match_allows_and_picks_best() -> None:
    out = _run(_input([
        _cand("weak", "no match here"),
        _cand("strong", "a clear summary"),
    ], criteria=["summary", "clear"]))
    assert out.verdict is Verdict.ALLOW
    assert out.chosen_strategy_id == "strong"
    assert out.scores["strong"] > out.scores["weak"]


def test_partial_match_at_half_defers_or_allows_at_boundary() -> None:
    # 0.5 is exactly the ALLOW threshold (>= 0.5) — a half-match ALLOWs.
    out = _run(_input([_cand("a", "a summary only")], criteria=["summary", "clear"]))
    assert out.verdict is Verdict.ALLOW
    assert out.scores["a"] == pytest.approx(0.5)


def test_partial_match_below_half_defers() -> None:
    # 1 of 3 criteria -> 0.333, which is > 0 but < 0.5 -> DEFER.
    out = _run(_input([_cand("a", "a summary only")], criteria=["summary", "clear", "concise"]))
    assert out.verdict is Verdict.DEFER
    assert out.scores["a"] == pytest.approx(1 / 3)


def test_no_match_denies() -> None:
    out = _run(_input([_cand("a", "nothing relevant")], criteria=["summary", "clear"]))
    assert out.verdict is Verdict.DENY
    assert out.scores["a"] == 0.0


def test_score_is_fraction_of_criteria_met() -> None:
    # "clear" appears, "summary" does not → 1 of 2 criteria → 0.5.
    out = _run(_input([_cand("a", "clear and crisp")], criteria=["summary", "clear"]))
    assert out.scores["a"] == pytest.approx(0.5)


def test_case_insensitive_matching() -> None:
    out = _run(_input([_cand("a", "A CLEAR SUMMARY")], criteria=["summary", "clear"]))
    assert out.verdict is Verdict.ALLOW


def test_reasoning_names_the_winner() -> None:
    out = _run(_input([_cand("a", "a clear summary")], criteria=["summary", "clear"]))
    assert "a" in out.reasoning