"""ARETĒ arbitration engine — non-compensatory virtue adjudication.

The arbitrator scores each candidate over the cardinal virtues, computes a
weighted "excellence" score, disqualifies any candidate that violates a
hard-gate virtue, and either ratifies a single winner (ALLOW), declines the
whole dispute (DENY), or defers because the field is not decisive (DEFER).

Deterministic and I/O-free: the reference implementation needs no external
verdict source. A custom :class:`VirtueScorer` may be injected to let an
external judge (an LLM gateway) supply the per-candidate virtue observations
while the arbitration *rule* stays local and auditable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from universal_mind.powers.judgment import CandidateOutput, Verdict

from .virtue import AreteError, CardinalVirtue, VirtueWeights


@dataclass(frozen=True)
class Dispute:
    """A dispute between competing candidate outputs to be arbitrated.

    Attributes:
        goal: The shared objective the candidates compete to satisfy.
        candidates: The competing candidates (each tagged with a strategy id).
        context: Optional ambient context (goal owner, budget, provenance…).
    """

    goal: str
    candidates: list[CandidateOutput]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VirtueScorecard:
    """Per-candidate virtue evaluation produced by arbitration."""

    candidate_strategy_id: str
    virtue_scores: dict[str, float]
    excellence: float
    disqualified: bool
    disqualify_reason: str | None = None


@dataclass(frozen=True)
class ArbitrationVerdict:
    """Binding outcome of an ARETĒ arbitration."""

    decision: Verdict
    winner_strategy_id: str | None
    ranking: list[str]
    scorecards: list[VirtueScorecard]
    reasoning: str


# Per-candidate virtue observation: mapper from cardinal virtue to a 0..1 score.
VirtueScorer = Callable[[CandidateOutput, Dispute], dict[CardinalVirtue, float]]


@runtime_checkable
class Arbitrator(Protocol):
    """Protocol for an ARETĒ arbitrator.

    Arbitration is a local, deterministic adjudication over material that has
    already been produced; it performs no I/O itself (though a
    :class:`VirtueScorer` may be backed by an external judge).
    """

    def arbitrate(self, dispute: Dispute) -> ArbitrationVerdict:
        """Return the binding verdict for a dispute."""
        ...


def _clamp(value: float) -> float:
    """Clamp a score into [0.0, 1.0]."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


# Small keyword signals per virtue, used only as a deterministic fallback when
# a candidate carries no precomputed ``metadata["virtues"]`` observation.
_KEYWORD_SIGNALS: dict[CardinalVirtue, tuple[str, ...]] = {
    CardinalVirtue.JUSTICE: (
        "fair", "just", "equitable", "rights", "consent", "impartial", "lawful",
    ),
    CardinalVirtue.WISDOM: (
        "accurate", "correct", "verified", "knowledge", "sound", "reasoned", "evidence",
    ),
    CardinalVirtue.COURAGE: (
        "honest", "candid", "direct", "accountable", "admits", "courage", "forthright",
    ),
    CardinalVirtue.TEMPERANCE: (
        "restrained", "measured", "conservative", "safe", "temperate", "bounded", "scoped",
    ),
}


def default_virtue_scorer(candidate: CandidateOutput, _dispute: Dispute) -> dict[CardinalVirtue, float]:
    """Deterministic default scorer over the cardinal virtues.

    Prefers a precomputed ``candidate.metadata["virtues"]`` observation (a dict
    of virtue-slug to 0..1 float); otherwise falls back to a keyword-overlap
    heuristic over the stringified output. No I/O; fully deterministic.
    """
    observed = candidate.metadata.get("virtues")
    if isinstance(observed, dict):
        return {
            virtue: _clamp(float(observed.get(virtue.value, 0.0)))
            for virtue in CardinalVirtue
        }
    text = str(candidate.output).lower()
    scores: dict[CardinalVirtue, float] = {}
    for virtue in CardinalVirtue:
        signals = _KEYWORD_SIGNALS[virtue]
        hits = sum(1 for token in signals if token in text)
        scores[virtue] = hits / len(signals)
    return scores


class InMemoryArbiter:
    """Reference ARETĒ arbitrator implementing the non-compensatory rule.

    Deterministic: given the same dispute, scorer, and weights it returns the
    same verdict every run (ties are broken by input order; excellence ties are
    ruled DEFER rather than guessed).
    """

    def __init__(self, weights: VirtueWeights | None = None, scorer: VirtueScorer | None = None) -> None:
        """Configure the arbiter.

        Args:
            weights: Virtue rubric; defaults to equal weights with Justice as
                the only hard gate.
            scorer: Per-candidate virtue scorer; defaults to
                :func:`default_virtue_scorer`.
        """
        self.weights = weights if weights is not None else VirtueWeights()
        self.scorer = scorer if scorer is not None else default_virtue_scorer

    def arbitrate(self, dispute: Dispute) -> ArbitrationVerdict:
        """Resolve a dispute to a binding verdict.

        An empty dispute (no candidates) is a legitimate *decline*: nothing can
        be ratified, so the verdict is DENY with no winner.

        Raises:
            AreteError: if the dispute is malformed (empty goal or
                missing/duplicate candidate strategy ids).
        """
        self._validate(dispute)
        if not dispute.candidates:
            return ArbitrationVerdict(
                decision=Verdict.DENY,
                winner_strategy_id=None,
                ranking=[],
                scorecards=[],
                reasoning="No candidates were submitted for arbitration.",
            )

        scorecards: list[VirtueScorecard] = []
        for candidate in dispute.candidates:
            observations = self.scorer(candidate, dispute)
            virtue_scores = {
                virtue.value: _clamp(observations.get(virtue, 0.0))
                for virtue in CardinalVirtue
            }
            weighted_float = sum(
                self.weights.weights[v] * virtue_scores[v.value] for v in CardinalVirtue
            ) / self.weights.total_weight()
            reason: str | None = None
            disqualified = False
            for gate in self.weights.hard_gate:
                if virtue_scores[gate.value] < self.weights.hard_gate_threshold:
                    disqualified = True
                    reason = (
                        f"fails hard-gate virtue {gate.value} "
                        f"({virtue_scores[gate.value]:.2f} < "
                        f"{self.weights.hard_gate_threshold:.2f})"
                    )
                    break
            scorecards.append(
                VirtueScorecard(
                    candidate_strategy_id=candidate.strategy_id,
                    virtue_scores=virtue_scores,
                    excellence=weighted_float,
                    disqualified=disqualified,
                    disqualify_reason=reason,
                )
            )

        disqualified_cards = [s for s in scorecards if s.disqualified]
        qualified_cards = [s for s in scorecards if not s.disqualified]

        # Stable ranking: qualified by excellence desc (ties by input order),
        # then disqualified appended (also sorted by excellence desc).
        ranking = (
            sorted(qualified_cards, key=lambda s: (-s.excellence, s.candidate_strategy_id))
            + sorted(disqualified_cards, key=lambda s: (-s.excellence, s.candidate_strategy_id))
        )
        ranking_ids = [s.candidate_strategy_id for s in ranking]

        if not ranking:
            raise AreteError("Internal error: ranking cannot be empty for a non-empty dispute")
        qualified_ranked = [s for s in ranking if not s.disqualified]
        if not qualified_ranked:
            return ArbitrationVerdict(
                decision=Verdict.DENY,
                winner_strategy_id=None,
                ranking=ranking_ids,
                scorecards=scorecards,
                reasoning="No candidate satisfies the hard-gate virtues.",
            )

        best = qualified_ranked[0]
        tied = any(
            abs(other.excellence - best.excellence) <= self.weights.tie_epsilon
            for other in qualified_ranked[1:]
        )
        if tied:
            return ArbitrationVerdict(
                decision=Verdict.DEFER,
                winner_strategy_id=None,
                ranking=ranking_ids,
                scorecards=scorecards,
                reasoning=f"Excellence tie at {best.excellence:.3f}; no decisive winner.",
            )
        if best.excellence < self.weights.accept_threshold:
            return ArbitrationVerdict(
                decision=Verdict.DENY,
                winner_strategy_id=None,
                ranking=ranking_ids,
                scorecards=scorecards,
                reasoning=(
                    f"Best qualified candidate {best.candidate_strategy_id} "
                    f"excellence {best.excellence:.3f} is below accept depth "
                    f"{self.weights.accept_threshold:.3f}."
                ),
            )
        return ArbitrationVerdict(
            decision=Verdict.ALLOW,
            winner_strategy_id=best.candidate_strategy_id,
            ranking=ranking_ids,
            scorecards=scorecards,
            reasoning=(
                f"Winner {best.candidate_strategy_id} with excellence "
                f"{best.excellence:.3f}. Rubric: {self.weights}."
            ),
        )

    @staticmethod
    def _validate(dispute: Dispute) -> None:
        """Raise :class:`AreteError` for malformed disputes."""
        if not dispute.goal or not dispute.goal.strip():
            raise AreteError("Dispute.goal must be a non-empty string")
        seen: set[str] = set()
        for candidate in dispute.candidates:
            if not candidate.strategy_id:
                raise AreteError("Every candidate must carry a non-empty strategy_id")
            if candidate.strategy_id in seen:
                raise AreteError(
                    f"Duplicate candidate strategy_id: {candidate.strategy_id}"
                )
            seen.add(candidate.strategy_id)