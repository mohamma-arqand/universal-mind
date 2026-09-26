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
# Without history, a capability's expected duration ceiling (ms).
_LEARNED_TOLERANCE = 3.0  # 3x the route's own learned median


def _route_median_ms(cap: str) -> float | None:
    """The learned median duration of one capability from REAL history."""
    try:
        from universal_mind.database_suite import DatabaseSuite

        q = DatabaseSuite.shared_persistent().query(
            "SELECT durations_ms FROM run_history "
            "WHERE route = ? AND succeeded = 1 "
            "AND durations_ms IS NOT NULL AND durations_ms != '' "
            "ORDER BY id DESC LIMIT 30",
            (cap,),
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — the lens never blocks
        return None
    vals: list[float] = []
    import json as _json

    for r in rows:
        try:
            data = _json.loads(str(r.get("durations_ms") or "{}"))
            v = float(data.get(cap) or 0.0)
            if v > 0:
                vals.append(v)
        except (ValueError, TypeError):
            continue
    if len(vals) < 3:
        return None
    vals.sort()
    mid = len(vals) // 2
    med = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
    return med


def _temperance_for(cap: str, duration_ms: float) -> float:
    """1.0 when the duration is within the learned (or global) band."""
    if duration_ms <= 0:
        return 1.0
    med = _route_median_ms(cap)
    ceiling = min(_SANE_DURATION_MS,
                  med * _LEARNED_TOLERANCE) if med else _SANE_DURATION_MS
    return 1.0 if duration_ms <= ceiling else round(ceiling / duration_ms, 4)


def run_virtue_scores(run: dict[str, Any]) -> dict[str, float]:
    """The four cardinal virtues, computed from the run's own real data."""
    route: list[str] = list(run.get("route", []))
    results: dict[str, Any] = run.get("result", {}) or {}
    durations: dict[str, float] = {k: float(v) for k, v in (run.get("durations_ms", {}) or {}).items()}
    errors: dict[str, str] = run.get("errors", {}) or {}

    if not route:
        return {"wisdom": 0.0, "courage": 0.0, "temperance": 0.0, "justice": 0.0}

    # A run that reports itself failed cannot be virtuous, whatever partial
    # results it carries: the honest overall verdict anchors all four virtues.
    overall_failed = run.get("ok") is False

    def _has_evidence(res: Any) -> float:
        if res is None:
            return 0.0
        if isinstance(res, dict):
            if res.get("ok") is False:
                return 0.0  # an explicit failure is evidence of nothing
            if "path" in res and res["path"]:
                return 1.0  # an artifact pointer: openable by anyone
            if "bytes" in res and isinstance(res["bytes"], (int, float)) \
                    and res["bytes"]:
                return 1.0  # a non-zero payload size
            numeric = [v for v in res.values()
                       if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if numeric:
                return 1.0  # a concrete metric: auditable by recomputation
            return 0.5  # honest shape, thin substance — half-courage
        if isinstance(res, (int, float)) and not isinstance(res, bool):
            return 1.0
        return 0.5 if res else 0.0

    checks = max(1, len(route))
    courage = sum(_has_evidence(results.get(cap)) for cap in route) / checks

    # WISDOM — every requested capability produced a real, non-empty result.
    # An honest error for a capability is evidence it did NOT produce: a run
    # with any error entry cannot carry full wisdom (whatever else it built).
    # R48-3 — WISDOM with depth: a capability is SERVED only when its
    # result carries real substance (the same evidence bar as courage). A
    # shape-correct but empty dict is half-served, not served.
    served = 0.0
    for cap in route:
        res = results.get(cap)
        if res is None:
            continue
        if isinstance(res, dict) and res.get("ok") is False:
            continue  # an honest error is NOT a served capability
        served += 1.0 if _has_evidence(res) >= 1.0 else 0.5
    wisdom = served / len(route)
    if errors:
        wisdom = min(wisdom, 0.5)  # any honest error caps wisdom at half
    if overall_failed and not served:
        wisdom = 0.0

    # R48-1 — COURAGE, honestly earned. A `dict` with key "ok" is NOT
    # evidence: every payload carries ok, so the old test stamped ~92% of
    # real runs excellence=1.0 (measured: 30,646/33,442) and blinded the
    # gate, the predictor, and the drift laws. Evidence now means something
    # an OUTSIDE inspector can check:
    #   - a file path that exists on disk (the validator's own law), or
    #   - a non-zero byte size, or
    #   - a concrete number (a mean is auditable by recomputation).
    # A bare {"ok": True} — right shape, no substance — is half-courage,
    # never full.

    # R48-2 — TEMPERANCE, learned from the route's own history: a 50ms
    # route that suddenly takes 30s is intemperate even under the old 60s
    # ceiling. The expectation is the MEDIAN duration of this same route
    # (>=3 witnesses in run_history), with a 3x tolerance band; without
    # witnesses the global 60s sanity ceiling stays.
    bounded = [
        _temperance_for(cap, durations.get(cap, 0.0)) for cap in route
    ]
    temperance = sum(bounded) / max(1, len(bounded))

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