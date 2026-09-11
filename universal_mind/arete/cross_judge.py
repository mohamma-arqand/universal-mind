"""Cross-model judging — a second, foreign judge adjudicates the first judge.

An arbiter that always agrees with itself can drift unnoticed. This module is the
anti-alignment layer: a *second* judge with an independently-configured rubric
re-arbitrates the same dispute, and the two verdicts are compared. Agreement is
reported as alignment confidence; disagreement is flagged — because when two
independently-tuned judges diverge, that divergence is itself evidence that the
decision is not robust.

Deterministic and local: the second judge is a :class:`InMemoryArbiter` with a
different :class:`VirtueWeights` rubric (no I/O, no shared state).
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.arete.arbiter import ArbitrationVerdict, Dispute, InMemoryArbiter
from universal_mind.arete.virtue import VirtueWeights


@dataclass(frozen=True)
class CrossJudgeResult:
    """The comparison of two independent judgments over the same dispute."""

    primary_winner: str | None
    second_winner: str | None
    aligned: bool                 # both judges picked the same winner
    primary_decision: str
    second_decision: str
    confidence: float             # 0..1, agreement strength
    explanation: str


def cross_judge(
    dispute: Dispute,
    primary_verdict: ArbitrationVerdict,
    *,
    secondary_weights: VirtueWeights | None = None,
) -> CrossJudgeResult:
    """Re-arbitrate with a foreign rubric and compare against the primary verdict.

    The second judge uses ``secondary_weights`` (default: a tempered rubric that
    raises the accept threshold and adds Courage as a second hard gate, so its
    ruling does not simply echo the primary). Agreement is decided per-winner and
    per-decision.
    """
    second = InMemoryArbiter(weights=secondary_weights if secondary_weights is not None else _foreign_weights())
    second_verdict = second.arbitrate(dispute)

    primary_winner = primary_verdict.winner_strategy_id
    second_winner = second_verdict.winner_strategy_id
    aligned = primary_winner is not None and primary_winner == second_winner

    if aligned:
        confidence = 1.0
        explanation = (
            f"two independent rubrics agree on {primary_winner!r} — alignment confidence high"
        )
    elif primary_winner is None and second_winner is None:
        confidence = 0.5
        explanation = "both judges declined/deferred (no winner) — inconclusive but not contradictory"
    else:
        confidence = 0.0
        explanation = (
            f"rubrics diverge: primary {primary_winner!r} vs second {second_winner!r} "
            "— the decision is not robust"
        )

    return CrossJudgeResult(
        primary_winner=primary_winner,
        second_winner=second_winner,
        aligned=aligned,
        primary_decision=primary_verdict.decision.value,
        second_decision=second_verdict.decision.value,
        confidence=confidence,
        explanation=explanation,
    )


def _foreign_weights() -> VirtueWeights:
    """A deliberately independent rubric (not a copy of the primary's default).

    Raises the accept threshold and adds Courage as a second hard gate, so the
    second judge is genuinely *foreign* — it may reject what the primary accepts.
    """
    from universal_mind.arete.virtue import CardinalVirtue

    return VirtueWeights(
        accept_threshold=0.7,
        hard_gate=frozenset({CardinalVirtue.JUSTICE, CardinalVirtue.COURAGE}),
    )