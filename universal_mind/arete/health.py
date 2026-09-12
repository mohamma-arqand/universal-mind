"""Judgment health — the mind watches its own judging for drift.

A judge that silently degrades (starts deferring everything, or keeps accepting
weaker and weaker work) is the charter's "expensive garbage-maker" in a
different guise. This module is the self-aware counterweight: it derives simple,
deterministic health signals from a lineage of judgments and raises a reasoned
*alert* when judging itself looks unhealthy — not by thresholds alone, but with
a plain explanation of *which* signal tripped and why it matters.

Pure and local: it reads judgment history, never mutates it.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode


@dataclass(frozen=True)
class JudgmentHealthSignal:
    """Named diagnostic with a value and whether it is concerning."""

    name: str
    value: float
    ok: bool
    note: str


@dataclass(frozen=True)
class JudgmentHealthReport:
    """The self-assessment of a judgment history."""

    signals: tuple[JudgmentHealthSignal, ...]
    unhealthy: bool
    summary: str


def assess_judgment_health(
    lineage: JudgmentLineage,
    *,
    defer_ratio: float = 0.5,
    min_decisions: int = 6,
    excellence_decline: float = 0.05,
) -> JudgmentHealthReport:
    """Derive health signals from a lineage and flag concerning patterns.

    Signals:
    - ``defer_rate``: fraction of DEFER verdicts (too high = the judge is
      failing to decide — a degenerate "I can't pick" posture).
    - ``excellence_trend``: whether accepted excellence is declining (too much
      = the judge keeps pushing work that is getting weaker).

    ``min_decisions`` suppresses alerts on tiny samples (an N of 2 can't be
    judged unhealthy); below it the report is ``healthy`` by construction.
    """
    nodes = lineage.nodes()
    if len(nodes) < min_decisions:
        return JudgmentHealthReport(
            signals=(),
            unhealthy=False,
            summary=f"insufficient decisions to assess ({len(nodes)} < {min_decisions})",
        )

    total = len(nodes)
    defers = sum(1 for n in nodes if n.decision == "deferred")
    defer_rate = defers / total if total else 0.0

    accepted = [n for n in nodes if n.decision == "promoted"]
    trend = _excellence_trend(accepted)

    signals = (
        JudgmentHealthSignal(
            name="defer_rate",
            value=round(defer_rate, 4),
            ok=defer_rate <= defer_ratio,
            note=f"{defers}/{total} decisions deferred",
        ),
        JudgmentHealthSignal(
            name="excellence_trend",
            value=round(trend, 4),
            ok=trend >= -excellence_decline,
            note="slope of accepted excellence over time",
        ),
    )
    unhealthy = any(not s.ok for s in signals)
    if unhealthy:
        bad = ", ".join(s.name for s in signals if not s.ok)
        summary = f"judgment appears unhealthy ({bad}) — consider re-weighting the rubric"
    else:
        summary = "judgment looks healthy"
    return JudgmentHealthReport(signals=signals, unhealthy=unhealthy, summary=summary)


def _excellence_trend(accepted: list[JudgmentNode]) -> float:
    """Linear slope of accepted excellence over the accepted sequence.

    Positive = excellence rising; negative = falling. Returns 0.0 for fewer than
    2 accepted nodes (no meaningful slope).
    """
    n = len(accepted)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(node.excellence for node in accepted) / n
    num = sum((x - mean_x) * (node.excellence - mean_y) for x, node in zip(xs, accepted, strict=True))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0