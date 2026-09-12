"""Hypothesis ensemble — hold several readings, converge on evidence.

A mind that locks into its first reading of an intent is exactly the "expensively
wrong" failure the charter warns about: one interpretation, one execution, one
costly mistake. This module is the ensemble layer: a goal is decomposed into
several *parallel* hypotheses (different decompositions, different emphases),
each is scored against evidence, and the ensemble reports a converged ranking —
the best hypothesis AND the live alternatives — so the mind can commit to a
reading without losing sight of the runners-up.

Deterministic and local: hypotheses are pure and scoring is a closed form over
their declared evidence weight and simplicity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hypothesis:
    """One parallel reading of an intent."""

    hypothesis_id: str
    reading: str
    evidence_weight: float          # 0..1, how much evidence supports this reading
    simplicity: float               # 0..1, higher = fewer moving parts
    tags: tuple[str, ...] = ()


def _score(h: Hypothesis) -> float:
    """Combine evidence weight and simplicity into a single converged score.

    Evidence dominates, but all else equal a simpler reading wins — a bias
    toward the least-assumptive interpretation.
    """
    return 0.7 * h.evidence_weight + 0.3 * h.simplicity


@dataclass(frozen=True)
class EnsembleResult:
    """The converged outcome of competing hypotheses."""

    ranked: tuple[Hypothesis, ...]      # best first
    best: Hypothesis | None
    alternatives: tuple[Hypothesis, ...]  # runners-up, still live
    converged: bool                      # True if a decisive margin separates best


class HypothesisEnsemble:
    """Score competing readings and report a converged ranking."""

    def __init__(self, *, margin: float = 0.1, min_alternatives: int = 2) -> None:
        self._margin = margin
        self._min_alternatives = min_alternatives

    def converge(self, hypotheses: list[Hypothesis]) -> EnsembleResult:
        """Rank hypotheses and decide whether the field has converged.

        ``converged`` is True only when the best reading beats the second by at
        least ``margin`` — otherwise the ensemble stays open (best is still
        reported, but the verdict is not decisive), which is the honest signal
        that more evidence is needed.
        """
        if not hypotheses:
            return EnsembleResult(ranked=(), best=None, alternatives=(), converged=False)

        ranked = tuple(sorted(hypotheses, key=lambda h: (-_score(h), h.hypothesis_id)))
        best = ranked[0]
        if len(ranked) > 1:
            second_score = _score(ranked[1])
            converged = _score(best) - second_score >= self._margin
        else:
            # A single hypothesis has no rival to beat: "converged" means several
            # readings resolved to one winner, not that one reading is present.
            # With nothing to compare against, the field is NOT converged.
            converged = False

        # Alternatives = the strongest runners-up (up to min_alternatives), which
        # remain live so the mind never loses sight of competing readings.
        alternatives = tuple(ranked[1:1 + self._min_alternatives])

        return EnsembleResult(ranked=ranked, best=best, alternatives=alternatives, converged=converged)


def score_hypothesis(h: Hypothesis) -> float:
    """Public accessor for a hypothesis's converged score (for inspection)."""
    return _score(h)