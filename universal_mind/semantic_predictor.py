"""R47 item 4 — the SEMANTIC anchor: prediction from MEANING, not just counts.

The route-count predictor (success_predictor.predict_success) sees chains;
this overlay sees WORDS. When the nearest past command by TF-IDF meaning is
close enough (similarity >= 0.5) and its runs tell a story, that story joins
the prediction — the semantic success rate blends with the chain's own
count-based probability (60/40 toward the chain's own evidence when it has
any; the anchor alone when the chain is unseen).

Honesty laws:
  - no sklearn, tiny history, or a too-distant anchor → NO anchor,
    the count-based prediction is returned untouched and says so;
  - the anchor is never fabricated: it is a real past command with real
    runs from run_history.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from universal_mind.success_predictor import Prediction, predict_success

_WORD = re.compile(r"[\u0600-\u06FF\w]+")


def _tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall(str(text)) if len(t) >= 2]


def _semantic_anchor(command: str) -> dict[str, Any] | None:
    """The nearest past command by TF-IDF + its real success rate."""
    from universal_mind.success_predictor import _store

    db = _store()
    try:
        q = db.query(
            "SELECT command, succeeded FROM run_history "
            "WHERE command IS NOT NULL AND command != ? "
            "ORDER BY id DESC LIMIT 400",
            (command,),
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — the lens never blocks
        return None
    if len(rows) < 2:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None

    past = [str(r["command"]) for r in rows]
    try:
        vec = TfidfVectorizer(tokenizer=_tokens, token_pattern=None)
        mtx = vec.fit_transform(past + [command])
    except ValueError:
        return None
    sims = cosine_similarity(mtx[-1], mtx[:-1])[0]
    best = int(sims.argmax())
    sim = float(sims[best])
    if sim < 0.5:
        return None
    # all real runs of that nearest command
    try:
        rq = db.query(
            "SELECT succeeded FROM run_history WHERE command = ? "
            "ORDER BY id DESC LIMIT 100",
            (past[best],),
        )
        rrows = rq.get("rows", []) if rq.get("ok") else []
    except Exception:  # noqa: BLE001
        return None
    if not rrows:
        return None
    wins = sum(1 for r in rrows if int(r["succeeded"]) == 1)
    return {
        "command": past[best],
        "similarity": round(sim, 4),
        "runs": len(rrows),
        "success_rate": round(wins / len(rrows), 4),
    }


def predict_semantic(command: str, route: tuple[str, ...]) -> Prediction:
    """The count-based prediction, enriched (or honestly untouched)."""
    base = predict_success(route)
    anchor = _semantic_anchor(command)
    if anchor is None:
        return base

    p_chain = base.success_probability
    p_anchor = float(anchor["success_rate"])
    if base.evidence_runs > 0:
        # the chain's own earned evidence still leads (60/40)
        blended = round(0.6 * p_chain + 0.4 * p_anchor, 4)
    else:
        # an unseen chain borrows the anchor's story wholesale
        blended = p_anchor
    if blended >= 0.9:
        tier, bar = "strong", 0.75
    elif blended >= 0.6:
        tier, bar = "medium", 0.80
    else:
        tier, bar = "weak", 0.90
    enriched = replace(base, success_probability=blended, tier=tier,
                       recommended_bar=bar,
                       semantic_anchor=anchor,
                       anchor_similarity=float(anchor["similarity"]))
    return enriched


def anchor_fa(anchor: dict[str, Any]) -> str:
    """One Persian line describing the semantic anchor."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    sim = str(round(float(anchor["similarity"]) * 100)).translate(fa)
    rate = str(round(float(anchor["success_rate"]) * 100)).translate(fa)
    runs = str(int(anchor["runs"])).translate(fa)
    return (f"مثل «{anchor['command']}» (شبیه {sim}٪، "
            f"{runs} اجرا، {rate}٪ موفق)")


__all__ = ["predict_semantic", "anchor_fa"]
