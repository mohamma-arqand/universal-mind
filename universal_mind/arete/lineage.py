"""Judgment lineage — the reasoning *behind* the standards, not just the winner.

A StandardKeeper knows the current standard. It does not know *why* each
proposal won or lost beyond the bare ALLOW/DENY/DEFER tag. This module reifies
that: every consideration is appended as a **reasoned judgment node** carrying
the contender, the verdict, the winning/losing rationale (from ARETĒ's own
reasoning), the soft-gate virtue scores, and the lineage depth it sat at. The
result is a queryable *tree of judgment* — the mind can explain not only what is
true now, but why earlier truths fell, and recover alternative branches that
were recently strong contenders but lost a head-to-head.

This is the "ONE INTEGRATED JUDGMENT" substrate made inspectable: judgment
history is data, not a side effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.arete.standard import (
    PromotionResult,
    StandardKeeper,
)
from universal_mind.powers.judgment import CandidateOutput


@dataclass(frozen=True)
class JudgmentNode:
    """One reasoned judgment: a contender, its fate, and *why*."""

    depth: int                    # lineage depth this consideration sat at
    contender: str                # the proposed standard's name
    decision: str                 # promoted / rejected / deferred
    reasoning: str                # ARETĒ's own explanation (never empty)
    excellence: float             # the contender's weighted excellence score
    justice: float                # the hard-gate virtue, for auditability


class JudgmentLineage:
    """Queryable history of every reasoned judgment a keeper has made.

    Wraps (not replaces) a :class:`StandardKeeper`: each ``consider`` is still
    arbitrated by the keeper's non-compensatory rule, but the lineage records the
    *reason* alongside the outcome. ``explain()`` returns the full justifying
    trail up to and including the current standard, so a decision is always
    backed by an auditable argument chain.
    """

    def __init__(self, keeper: StandardKeeper) -> None:
        self._keeper = keeper
        self._nodes: list[JudgmentNode] = []

    @classmethod
    def from_nodes(cls, keeper: StandardKeeper, nodes: list[JudgmentNode]) -> JudgmentLineage:
        """Build a lineage pre-populated with nodes (for analysis/tests)."""
        instance = cls(keeper)
        instance._nodes = list(nodes)
        return instance

    @property
    def keeper(self) -> StandardKeeper:
        return self._keeper

    def consider(self, proposal: CandidateOutput) -> PromotionResult:
        """Arbitrate via the keeper and append a reasoned node for the outcome."""
        result = self._keeper.consider(proposal)
        scorecards = getattr(result.verdict, "scorecards", []) or []
        contender_card = next(
            (c for c in scorecards if c.candidate_strategy_id == proposal.strategy_id),
            None,
        )
        excellence = contender_card.excellence if contender_card is not None else 0.0
        justice = (contender_card.virtue_scores.get("justice", 0.0)
                   if contender_card is not None else 0.0)
        reasoning = result.verdict.reasoning if result.verdict is not None else result.decision.value
        self._nodes.append(
            JudgmentNode(
                depth=getattr(result.current_standard, "promotion_depth", 0),
                contender=proposal.strategy_id,
                decision=result.decision.value,
                reasoning=reasoning,
                excellence=round(excellence, 4),
                justice=round(justice, 4),
            )
        )
        return result

    def nodes(self) -> tuple[JudgmentNode, ...]:
        """All reasoned judgments, oldest first."""
        return tuple(self._nodes)

    def explain(self, *, last: int = 5) -> list[str]:
        """Return the most recent justifying trail as human-readable reasons."""
        return [
            f"[{n.decision}] {n.contender} @depth {n.depth} — {n.reasoning}"
            for n in self._nodes[-last:]
        ]

    def rejected_branches(self) -> tuple[str, ...]:
        """Names of contenders that lost a head-to-head (recoverable alternatives)."""
        return tuple(n.contender for n in self._nodes if n.decision == "rejected")

    def best_losing_contender(self) -> JudgmentNode | None:
        """The highest-excellence contender that still lost — the closest near-miss."""
        losers = [n for n in self._nodes if n.decision == "rejected"]
        if not losers:
            return None
        return max(losers, key=lambda n: n.excellence)

    def count_by_decision(self) -> dict[str, int]:
        """Tally promoted / rejected / deferred across the lineage."""
        counts: dict[str, int] = {}
        for n in self._nodes:
            counts[n.decision] = counts.get(n.decision, 0) + 1
        return counts