"""Causal reasoning — beyond correlation, toward "why" and "what would change it".

Observing two events co-occur is not enough to know one *causes* the other. This
module is the causal layer: given an ordered trace of (cause-candidate, effect)
events, it tests each candidate with the classic intervention question — "if the
cause were removed, would the effect still happen?" — and separates the
*necessary* causes (effect never happens without them) from the *incidental*
ones (they co-occur but do not drive the effect).

That distinction is the seed of real "why" reasoning: a mind that can say which
factor actually controls an outcome, not merely which factor sits next to it.

Deterministic and local: it reads an ordered trace, never mutates it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    """One observed event in a run trace."""

    event_id: str
    cause: str            # the candidate cause this event tests
    effect: bool          # did the effect occur?
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CausalFinding:
    """The causal verdict for one candidate cause."""

    cause: str
    necessary: bool         # effect never occurs without this cause
    support_ratio: float    # P(effect | cause present)
    absence_ratio: float    # P(effect | cause absent) — the intervention signal
    explanation: str


def infer_causes(events: list[TraceEvent]) -> tuple[CausalFinding, ...]:
    """Test each candidate cause with the intervention question.

    For each distinct cause, compare how often the effect occurs *with* the cause
    present versus *with* it absent. A cause is ``necessary`` when the effect
    never occurs in its absence (absence_ratio == 0) and does occur when present —
    the "remove the cause, the effect goes away" signal that separates causation
    from mere co-occurrence.
    """
    causes: list[str] = []
    for e in events:
        if e.cause not in causes:
            causes.append(e.cause)

    findings: list[CausalFinding] = []
    for cause in causes:
        present = [e for e in events if e.cause == cause]
        absent = [e for e in events if e.cause != cause]

        support = sum(1 for e in present if e.effect) / len(present) if present else 0.0
        absence_effect = sum(1 for e in absent if e.effect) / len(absent) if absent else 0.0

        necessary = bool(present) and support > 0.0 and absence_effect == 0.0

        if necessary:
            explanation = (
                f"'{cause}' is necessary: the effect occurs with it and never without it"
            )
        elif support > 0.0 and absence_effect > 0.0:
            explanation = (
                f"'{cause}' is incidental: the effect occurs with and without it, so it co-occurs but does not control the effect"
            )
        else:
            explanation = f"'{cause}' does not drive the effect (insufficient support)"

        findings.append(
            CausalFinding(
                cause=cause,
                necessary=necessary,
                support_ratio=round(support, 4),
                absence_ratio=round(absence_effect, 4),
                explanation=explanation,
            )
        )
    return tuple(findings)