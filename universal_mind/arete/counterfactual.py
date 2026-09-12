"""Counterfactual reasoning — would the judgment survive if its premise were false?

A verdict that only answers "which is best?" can be right by luck: the winning
candidate may win *because* of a single fragile premise, and a plain score never
tells you that. This module is the counterfactual layer: it re-arbitrates the
dispute under a reversed assumption (a "what if the premise were false?" world)
and reports whether the decision is *robust* (the winner still wins) or *fragile*
(the winner collapses under the reversed premise).

That robustness is the difference between a guess and a reasoned conclusion — it
is the trace of *why* a decision holds, not just *that* it holds.

Deterministic and local: it reuses the same :class:`InMemoryArbiter` rule and
never mutates the original dispute or verdict.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.arete.arbiter import ArbitrationVerdict, Dispute, InMemoryArbiter
from universal_mind.powers.judgment import CandidateOutput


class CounterfactualError(Exception):
    """Raised when a counterfactual check cannot even be attempted."""


@dataclass(frozen=True)
class CounterfactualResult:
    """The outcome of re-arbitrating under a reversed premise."""

    original_winner: str | None
    robust: bool                    # True if the winner survives the reversed premise
    counterfactual_winner: str | None
    explanation: str
    # Evidence: the virtues that were reversed and how they changed.
    reversed_dimension: str = ""
    original_value: float = 0.0
    reversed_value: float = 0.0


def _reverse_candidate(candidate: CandidateOutput, dimension: str) -> CandidateOutput:
    """Return a copy of the candidate with the named premise dimension reversed.

    The premise lives in ``metadata["virtues"]``; reversing a virtue means
    flipping it toward the opposite end of [0,1] (a high score becomes low).
    """
    virtues = dict(candidate.metadata.get("virtues", {})) if isinstance(candidate.metadata, dict) else {}
    current = float(virtues.get(dimension, 0.5))
    virtues[dimension] = 1.0 - current
    return CandidateOutput(
        strategy_id=candidate.strategy_id,
        output=candidate.output,
        metadata={**candidate.metadata, "virtues": virtues},
    )


def counterfactual_check(
    dispute: Dispute,
    verdict: ArbitrationVerdict,
    *,
    assumption: str = "wisdom",
    arbiter: InMemoryArbiter | None = None,
) -> CounterfactualResult:
    """Re-arbitrate the dispute with the named assumption reversed.

    ``assumption`` is a virtue slug (default ``wisdom``) treated as the load-bearing
    premise. The whole candidate field is copied with that virtue flipped, and the
    arbiter is run again. The original winner is *robust* if it still wins under the
    reversed premise; otherwise the decision is *fragile* (its correctness hinged on
    that premise).
    """
    if not dispute.candidates:
        raise CounterfactualError("cannot counterfactually check an empty dispute")

    original_winner = verdict.winner_strategy_id
    # Report the reversed dimension's value from the CANDIDATE's declared virtues
    # (the actual premise that _reverse_candidate flips), not from the scorecard —
    # the scorecard back-fills undeclared virtues with 0.0, which would fabricate
    # original=0.0 / reversed=1.0 for a dimension the candidate never declared.
    original_value = 0.0
    if original_winner is not None:
        for c in dispute.candidates:
            if c.strategy_id == original_winner:
                virtues = c.metadata.get("virtues", {}) if isinstance(c.metadata, dict) else {}
                original_value = float(virtues.get(assumption, 0.5))
                break

    effective_arbiter = arbiter if arbiter is not None else InMemoryArbiter()

    reversed_candidates = [_reverse_candidate(c, assumption) for c in dispute.candidates]
    reversed_dispute = Dispute(
        goal=dispute.goal,
        candidates=reversed_candidates,
        context=dict(dispute.context) | {"counterfactual": assumption},
    )
    reversed_verdict = effective_arbiter.arbitrate(reversed_dispute)

    counterfactual_winner = reversed_verdict.winner_strategy_id
    if original_winner is None:
        robust = False  # no winner to be robust; the decision is already indecisive
        explanation = (
            "no original winner (verdict was denied/deferred); "
            f"counterfactual winner: {counterfactual_winner}"
        )
    else:
        robust = counterfactual_winner == original_winner
        if robust:
            explanation = (
                f"winner {original_winner!r} survives reversing {assumption!r} "
                f"(robust — the decision does not hinge on that premise)"
            )
        else:
            explanation = (
                f"winner {original_winner!r} collapses when {assumption!r} is reversed "
                f"(fragile — the decision hinged on that premise); "
                f"counterfactual winner: {counterfactual_winner!r}"
            )

    reversed_value = 1.0 - original_value
    return CounterfactualResult(
        original_winner=original_winner,
        robust=robust,
        counterfactual_winner=counterfactual_winner,
        explanation=explanation,
        reversed_dimension=assumption,
        original_value=original_value,
        reversed_value=reversed_value,
    )