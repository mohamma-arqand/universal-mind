"""ARETĒ over real runs — every super-platform execution is virtue-judged.

The project's core principle is that judgment is not a scoreboard bolted on at
the end: it must inspect real work. This module is the bridge that finally
gives the platform's OWN runs to the ARETĒ arbitrator — the same non-compensatory
virtue arbitration that judges specialist disputes now judges what the
integrated programs actually produced.

The judgment is computed FROM the run's own data (no LLM, no guess):
- WISDOM: did every requested capability produce a real, non-empty result?
- COURAGE: does the output carry honest evidence (paths, bytes, durations)?
- TEMPERANCE: was the work scoped — no capability ran longer than a sane bound?
- JUSTICE: were all requested capabilities served equally (none silently dropped)?

The verdict is recorded into the run history so the advisor learns not just
"did it succeed" but "how excellent was it" — a richer learning signal.
"""

from __future__ import annotations

from typing import Any

from universal_mind.arete.arbiter import (
    ArbitrationVerdict,
    Dispute,
    InMemoryArbiter,
)
from universal_mind.powers.judgment import CandidateOutput

# A single capability that takes longer than this is intemperate (unbounded work).
_SANE_DURATION_MS = 60_000.0


def run_virtue_scores(run: dict[str, Any]) -> dict[str, float]:
    """The four cardinal virtues, computed from the run's own real data."""
    route: list[str] = list(run.get("route", []))
    results: dict[str, Any] = run.get("result", {}) or {}
    durations: dict[str, float] = {k: float(v) for k, v in (run.get("durations_ms", {}) or {}).items()}
    errors: dict[str, str] = run.get("errors", {}) or {}

    if not route:
        return {"wisdom": 0.0, "courage": 0.0, "temperance": 0.0, "justice": 0.0}

    # WISDOM — every requested capability produced a real, non-empty result.
    served = [cap for cap in route if cap in results and results[cap] is not None]
    wisdom = len(served) / len(route)

    # COURAGE — the output carries inspectable evidence: an artifact pointer
    # (path/bytes) OR a concrete metric value (a number IS its own evidence —
    # a mean is auditable by recomputation). Only an empty/absent result is
    # evidence-less.
    evidence_hits = 0
    checks = 0
    for cap in route:
        res = results.get(cap)
        checks += 1
        if isinstance(res, dict):
            if any(k in res for k in ("path", "bytes", "ok")) or any(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in res.values()
            ):
                evidence_hits += 1
        elif res is not None:
            evidence_hits += 1
    courage = evidence_hits / checks

    # TEMPERANCE — no capability ran unboundedly long.
    bounded = [
        1.0 if durations.get(cap, 0.0) <= _SANE_DURATION_MS else 0.0
        for cap in route
    ]
    temperance = sum(bounded) / len(bounded)

    # JUSTICE — no capability was silently dropped: every route entry has either
    # a result or an honest error, and errors are reported not hidden.
    accounted = [cap for cap in route if cap in results or cap in errors]
    justice = len(accounted) / len(route)

    return {
        "wisdom": round(wisdom, 4),
        "courage": round(courage, 4),
        "temperance": round(temperance, 4),
        "justice": round(justice, 4),
    }


def judge_run(run: dict[str, Any]) -> dict[str, Any]:
    """Virtue-judge one real super-platform run; returns the scorecard + verdict.

    Uses the REAL VirtueArbiter (non-compensatory: a single failing virtue can
    disqualify), with the run itself as the single candidate. The verdict's
    reasoning is returned verbatim for the Persian report.
    """
    scores = run_virtue_scores(run)
    candidate = CandidateOutput(
        strategy_id="the-integrated-platform",
        output=run.get("result", {}),
        metadata={"virtues": {k: v for k, v in scores.items()}},
    )
    dispute = Dispute(
        goal=str(run.get("command", "اجرای فرمان")),
        candidates=[candidate],
    )
    verdict: ArbitrationVerdict = InMemoryArbiter().arbitrate(dispute)
    return {
        "scores": scores,
        "excellence": verdict.scorecards[0].excellence if verdict.scorecards else 0.0,
        "disqualified": verdict.scorecards[0].disqualified if verdict.scorecards else True,
        "disqualify_reason": (verdict.scorecards[0].disqualify_reason if verdict.scorecards else "no scorecard"),
        "reasoning": verdict.reasoning,
    }


__all__ = ["judge_run", "run_virtue_scores"]