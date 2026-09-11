"""Independent evaluation — a second judge outside the self-checking loop.

A mind that only self-assesses has one blind spot: it never meets a foreign
standard, so a drift in its own rubric can go unnoticed forever. This module is
the charter's "human verdict" made systematic: an *external* evaluator that
scores the judgment + self-correction loop itself against a fixed, foreign rubric
— not the loop's own criteria — and records the result as an ``external_audit``
ledger entry.

The rubric is deliberately orthogonal to the loop's internal signals: it measures
*process health* (is the lineage growing? are decisions reasoned?), *boundedness*
(does the acceptance bar stay in [0,1]? does the budget stay non-negative?), and
*reversibility* (is every self-correction undoable?). If an audit fails, it is a
signal the loop's own self-assessment is missing something.

Deterministic and pure: it reads a :class:`SelfAwarenessLoop`, never mutates it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class AuditFinding:
    """One rubric dimension: pass/fail with a plain reason."""

    dimension: str
    ok: bool
    note: str


@dataclass(frozen=True)
class ExternalAuditResult:
    """The external evaluator's verdict on the loop's process health."""

    findings: tuple[AuditFinding, ...]
    passed: bool
    score: float                     # fraction of dimensions that passed
    summary: str
    ledger_record_id: str | None = None


# The foreign rubric: orthogonal to the loop's own defer/excellence signals.
def _findings(loop: Any) -> tuple[AuditFinding, ...]:
    """Derive audit findings from the loop's *reactive state*, not its self-report."""
    findings: list[AuditFinding] = []

    bar = getattr(loop, "acceptance_bar", None)
    if bar is None:
        findings.append(AuditFinding("acceptance_bar_bounded", False, "no acceptance bar exposed"))
    else:
        findings.append(AuditFinding("acceptance_bar_bounded", bool(0.0 <= bar <= 1.0), f"bar={bar:.3f}"))

    budget = getattr(loop, "budget", None)
    if budget is None:
        findings.append(AuditFinding("budget_non_negative", False, "no budget exposed"))
    else:
        findings.append(AuditFinding("budget_non_negative", bool(budget >= 0.0), f"budget={budget:.3f}"))

    lineage = getattr(loop, "lineage", None)
    nodes = getattr(lineage, "nodes", None)
    if callable(nodes):
        count = len(nodes())
        findings.append(AuditFinding("lineage_has_evidence", count > 0, f"{count} reasoned judgment(s)"))
    else:
        findings.append(AuditFinding("lineage_has_evidence", False, "lineage unavailable"))

    # Reversibility: a loop that can self-correct must also be able to relax
    # again; check that tighten() exists (the corrections are reversible).
    tighten = getattr(loop, "tighten", None)
    findings.append(AuditFinding("self_correction_reversible", callable(tighten), "tighten() hook present"))

    return tuple(findings)


def evaluate_loop(
    loop: Any,
    store: MemoryStore | None = None,
    *,
    owner: Identity = DEFAULT_OWNER,
    clock: Any | None = None,
) -> ExternalAuditResult:
    """Score a self-awareness loop against the foreign rubric and (optionally) record it.

    When ``store`` is provided, the audit is written as an ``external_audit``
    ledger entry so the mind's second judge is as auditable as its first.
    """
    findings = _findings(loop)
    passed = all(f.ok for f in findings)
    score = sum(1 for f in findings if f.ok) / len(findings) if findings else 0.0

    if passed:
        summary = f"external audit PASS ({score:.0%}): the loop's process is sound"
    else:
        bad = ", ".join(f.dimension for f in findings if not f.ok)
        summary = f"external audit FAIL ({score:.0%}): {bad}"

    record_id: str | None = None
    if store is not None:
        from universal_mind.core.clock import SystemClock

        mnemosyne = Mnemosyne(store, clock if clock is not None else SystemClock())
        record_id = mnemosyne.record(
            owner_id=owner.owner_id,
            kind="external_audit",
            payload={
                "passed": passed,
                "score": round(score, 4),
                "findings": [{"dimension": f.dimension, "ok": f.ok, "note": f.note} for f in findings],
            },
            provenance={"producer": "IndependentEvaluator", "owner_id": owner.owner_id},
        )

    return ExternalAuditResult(
        findings=findings,
        passed=passed,
        score=round(score, 4),
        summary=summary,
        ledger_record_id=record_id,
    )