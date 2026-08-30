"""Judgment power: score candidate outputs, return Verdict.

Spec concept: The ability to evaluate and rank candidate outputs from
multiple strategies, producing a final verdict.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Verdict(str, Enum):
    """Judgment verdict on a candidate output."""
    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"


@dataclass(frozen=True)
class CandidateOutput:
    """A candidate output to be judged."""
    strategy_id: str
    output: Any
    metadata: dict[str, Any]


@dataclass(frozen=True)
class JudgmentInput:
    """Input for judgment evaluation."""
    goal: str
    success_criteria: list[str]
    candidates: list[CandidateOutput]
    context: dict[str, Any]


@dataclass(frozen=True)
class JudgmentOutput:
    """Output from judgment evaluation."""
    verdict: Verdict
    chosen_strategy_id: str | None
    scores: dict[str, float]  # strategy_id -> score (0.0 to 1.0)
    reasoning: str


@runtime_checkable
class Judgment(Protocol):
    """Protocol for judging candidate outputs.

    The Judgment power evaluates multiple candidate outputs against
    success criteria and produces a verdict with scores and reasoning.
    """

    async def judge(self, input: JudgmentInput) -> JudgmentOutput:
        """Score candidate outputs and return a verdict.

        Args:
            input: JudgmentInput with goal, criteria, candidates, context

        Returns:
            JudgmentOutput with verdict, chosen strategy, scores, reasoning
        """
        ...


class InMemoryJudgment:
    """Reference in-memory implementation of Judgment (no I/O)."""

    async def judge(self, input: JudgmentInput) -> JudgmentOutput:
        if not input.candidates:
            return JudgmentOutput(
                verdict=Verdict.DENY,
                chosen_strategy_id=None,
                scores={},
                reasoning="No candidates provided",
            )

        # Simple scoring: count how many success criteria are met
        scores = {}
        for candidate in input.candidates:
            score = 0.0
            output_str = str(candidate.output).lower()
            for criterion in input.success_criteria:
                if criterion.lower() in output_str:
                    score += 1.0 / len(input.success_criteria)
            scores[candidate.strategy_id] = score

        # Choose best
        best_strategy = max(scores, key=scores.get)
        best_score = scores[best_strategy]

        if best_score >= 0.5:
            verdict = Verdict.ALLOW
        elif best_score > 0:
            verdict = Verdict.DEFER
        else:
            verdict = Verdict.DENY

        return JudgmentOutput(
            verdict=verdict,
            chosen_strategy_id=best_strategy,
            scores=scores,
            reasoning=f"Best score: {best_score:.2f} for {best_strategy}",
        )