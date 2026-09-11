"""Provable policy — every allow/deny as a verifiable reason chain, not one string.

A decision described only by a sentence cannot be *checked*; it must be trusted.
This module is the provability layer: it turns an arbitration verdict into a
structured chain of reason *steps*, each independently verifiable (which gate
held, which score was measured, which threshold was applied), so a decision can
be audited step-by-step. "Why did you allow/deny?" becomes a replayable trace.

Deterministic and pure: it reads a verdict, produces an immutable trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.arete.arbiter import ArbitrationVerdict
from universal_mind.powers.judgment import Verdict


@dataclass(frozen=True)
class PolicyStep:
    """One verifiable step in a decision's reason chain."""

    step: str                 # human-readable description of this step
    check: str                # what to verify (gate / measurement / threshold)
    value: Any                # the value that was checked
    passed: bool


@dataclass(frozen=True)
class PolicyTrace:
    """The full provable reason chain for a decision."""

    decision: str
    winner: str | None
    steps: tuple[PolicyStep, ...]
    verifiable: bool           # True if every step carries a concrete check


def trace_verdict(verdict: ArbitrationVerdict) -> PolicyTrace:
    """Decompose a verdict into a verifiable reason chain.

    Steps are derived from the verdict's own scorecards: for each candidate, a
    step records its measured excellence; the winner additionally records the
    hard-gate pass. A declined/deferred verdict records the reason as a single
    non-measured step (still verifiable as "no winner").
    """
    steps: list[PolicyStep] = []
    for card in verdict.scorecards:
        steps.append(
            PolicyStep(
                step=f"candidate {card.candidate_strategy_id} excellence",
                check="measurement",
                value=round(card.excellence, 4),
                passed=not card.disqualified,
            )
        )
        if card.disqualified and card.disqualify_reason:
            steps.append(
                PolicyStep(
                    step=f"hard-gate for {card.candidate_strategy_id}",
                    check="hard_gate",
                    value=card.disqualify_reason,
                    passed=False,
                )
            )

    if verdict.winner_strategy_id is not None:
        steps.append(
            PolicyStep(
                step=f"winner {verdict.winner_strategy_id} ratified",
                check="winner",
                value=verdict.winner_strategy_id,
                passed=True,
            )
        )
    elif verdict.decision in (Verdict.DENY, Verdict.DEFER):
        steps.append(
            PolicyStep(
                step="no winner ratified",
                check="no_winner",
                value=verdict.decision.value,
                passed=True,
            )
        )

    verifiable = all(s.value is not None for s in steps)
    return PolicyTrace(
        decision=verdict.decision.value,
        winner=verdict.winner_strategy_id,
        steps=tuple(steps),
        verifiable=verifiable,
    )