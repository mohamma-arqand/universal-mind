"""The success predictor — ARETĒ's expectation, BEFORE the run.

Learns from the operator's own history: for a candidate chain, what fraction
of its past runs succeeded, with what mean excellence? The prediction is
Bayesian-honest (Laplace smoothing) and drives a RISK TIER:

  strong  (p >= 0.9)   → the ordinary quality-gate bar (0.75)
  medium  (0.6..0.9)   → a slightly stricter bar (0.80)
  weak    (p < 0.6)    → the strict bar (0.90): the rival search runs, and a
                         failed primary actually STOPS the chain honestly

Unseen chains get the global success rate (never a blind 1.0 — the
'absence-as-success' law, at the prediction level).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.database_suite import DatabaseSuite


@dataclass(frozen=True)
class Prediction:
    """The pre-run expectation for one chain."""

    route: tuple[str, ...]
    success_probability: float   # Laplace-smoothed, 0..1
    evidence_runs: int            # how many real runs back it
    tier: str                    # strong / medium / weak
    recommended_bar: float       # the quality-gate bar this chain earned
    semantic_anchor: dict[str, Any] | None = None  # R47-4: nearest past command
    anchor_similarity: float = 0.0  # R47-4: its TF-IDF similarity, 0 when none


def _route_key(route: tuple[str, ...]) -> str:
    return ",".join(route)


def _store() -> DatabaseSuite:
    """The shared persistent store (R43: one truth, isolate-friendly)."""
    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


def predict_success(route: tuple[str, ...]) -> Prediction:
    """The chain's earned expectation from the operator's real history."""
    db = _store()
    key = _route_key(route)
    try:
        chain_q = db.query(
            "SELECT succeeded FROM run_history WHERE route = ? "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
            "ORDER BY id DESC LIMIT 200",
            (key,),
        )
        rows = chain_q.get("rows", []) if chain_q.get("ok") else []
    except Exception:  # noqa: BLE001 — prediction is a lens, never a blocker
        rows = []

    if rows:
        wins = sum(1 for r in rows if int(r["succeeded"]) == 1)
        n = len(rows)
        # Laplace smoothing keeps small evidence honest: 1/1 is ~0.75, not 1.0
        p = (wins + 1.0) / (n + 2.0)
        evidence = n
    else:
        # An UNSEEN chain inherits the global success rate — never blind 1.0
        try:
            glob_q = db.query(
                "SELECT AVG(CAST(succeeded AS REAL)) AS p, COUNT(*) AS n FROM run_history"
            )
            gp = float(glob_q["rows"][0]["p"] or 0.5)
            gn = int(glob_q["rows"][0]["n"] or 0)
        except Exception:  # noqa: BLE001
            gp, gn = 0.5, 0
        p = gp if gn > 0 else 0.5
        evidence = 0

    if p >= 0.9:
        tier, bar = "strong", 0.75
    elif p >= 0.6:
        tier, bar = "medium", 0.80
    else:
        tier, bar = "weak", 0.90
    return Prediction(
        route=route,
        success_probability=round(p, 4),
        evidence_runs=evidence,
        tier=tier,
        recommended_bar=bar,
    )


def prediction_fa(prediction: Prediction) -> str:
    """The prediction rendered as fluent Persian."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    tier_fa = {"strong": "قوی", "medium": "متوسط", "weak": "پرریسک"}[prediction.tier]
    pct = str(round(prediction.success_probability * 100)).translate(fa)
    evidence = str(prediction.evidence_runs).translate(fa)
    return (
        f"پیشبینی: احتمال موفقیت {pct}٪ (شواهد: {evidence} اجرا) — "
        f"ریسکِ {tier_fa}، آستانهی داوری {str(int(prediction.recommended_bar * 100)).translate(fa)}٪"
    )


__all__ = ["Prediction", "predict_success", "prediction_fa"]