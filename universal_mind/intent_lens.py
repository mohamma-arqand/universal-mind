"""The intent lens — the router's fourth dimension.

Word-matching alone is blind: «بکش» and «رسم کن» and «هیستوگرامش کن» all mean
chart, but which ORDER of capabilities fits THIS sentence? The lens scores
every candidate ordering the engine can form, from the operator's own real
history — no external LLM, only what this store has earned:

  1. CHAIN EVIDENCE — the exact chain's past success rate (Laplace-smoothed)
  2. FLOW EVIDENCE — the chain's own producer→consumer flows that really fired
  3. SEMANTIC OVERLAP — char-gram similarity between the command and each
     capability's Persian vocabulary (a word-level match is the lens floor)
  4. STANDING — the chain that became the operator's standard (3+ wins, 0.9+)

The lens NEVER overrides an explicit intent — it only ranks the orderings
the router already accepts, and it ranks them BEFORE the gate spends real
runs on the wrong ones first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from universal_mind.database_suite import DatabaseSuite
from universal_mind.success_predictor import predict_success


def _ngrams(text: str, n: int = 3) -> set[str]:
    """Char-gram set, right-to-left text included."""
    t = text.replace(" ", "")
    return {t[i: i + n] for i in range(max(0, len(t) - n + 1))} if len(t) >= n else {t}


def _similarity(a: str, b: str) -> float:
    """Jaccard over char-grams; 1.0 when identical."""
    ga, gb = _ngrams(a), _ngrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


@dataclass(frozen=True)
class ScoredRoute:
    """One ordering, with the WHY rendered as numbers."""

    route: tuple[str, ...]
    score: float
    chain_evidence: float
    flow_evidence: float
    semantic: float
    standing: bool
    reasons_fa: tuple[str, ...] = field(default_factory=tuple)


_VOCAB_HINTS: dict[str, tuple[str, ...]] = {
    # capability → the Persian phrases that historically select it
    "chart": ("نمودار", "رسم", "بکش", "هیستوگرام", "خطی", "ستونی", "میله"),
    "pdf": ("گزارش", "پی دی اف", "چاپ", "سند", "pdf"),
    "image": ("تصویر", "عکس", "پیکسل", "کشیده"),
    "data": ("میانگین", "داده", "آمار", "عدد", "محاسبه", "تعداد"),
    "archive": ("بایگانی", "فشرده", "zip", "ذخیره"),
    "database": ("جدول", "پایگاه", "ذخیره کرد", "بخوان"),
    "notify": ("هشدار", "اعلان", "خبر", "بگو"),
    "clipboard": ("کلیپبورد", "یادداشت", "کپی", "بگذار"),
    "vision": ("تحلیل تصویر", "بینایی", "ببین", "تشخیص"),
    "speech": ("بلند بخوان", "صحبت", "بگو بلند", "تلفظ"),
    "ocr": ("ocr", "بخوان تصویر", "متن تصویر"),
    "webfetch": ("وب", "سایت", "اینترنت", "جستجو", "دانلود", "ترجمه"),
    "excel": ("اکسل", "جدول", "خونه", "صفحه گسترده"),
    "compute": ("محاسبه", "حساب", "جمع", "ضرب", "تقسیم"),
}


def score_route(route: tuple[str, ...], command: str) -> ScoredRoute:
    """Rank one ordering against this sentence, from real history."""
    # 1. chain evidence — Laplace-smoothed, honest — BUT an UNSEEN chain
    # inherits no chain-evidence here: the global rate is a fair PRIOR for
    # the gate's risk bar, yet as a RANKING signal it would let a chain the
    # operator never ran outrank the one they ran 450 times.
    pred = predict_success(route)
    chain_evidence = pred.success_probability if pred.evidence_runs > 0 else 0.0

    # 2. flow evidence — did THIS chain's flows really fire before?
    db = DatabaseSuite(persistent=True)
    flow_evidence = 0.0
    try:
        key = ",".join(route)
        q = db.query(
            "SELECT flows FROM run_history WHERE route = ? AND succeeded = 1 "
            "ORDER BY id DESC LIMIT 200",
            (key,),
        )
        rows = q.get("rows", []) if q.get("ok") else []
        flow_evidence = min(1.0, (sum(1 for r in rows if (r.get("flows") or "").strip()) / 200) * 2)
    except Exception:  # noqa: BLE001 — the lens never blocks a run
        flow_evidence = 0.0

    # 3. semantic overlap — every capability in the chain must be spoken to
    semantic = 0.0
    if route:
        per_cap = []
        for cap in route:
            hints = _VOCAB_HINTS.get(cap, (cap,))
            per_cap.append(max(_similarity(command, h) for h in hints))
        semantic = sum(per_cap) / len(per_cap)

    # 4. standing — the operator's own standard chain
    standing = False
    try:
        from universal_mind.history_analytics import standing_chain

        st = standing_chain()
        standing = bool(st.get("ok") and tuple(st.get("chain", ())) == route)
    except Exception:  # noqa: BLE001
        standing = False

    score = (
        0.45 * chain_evidence
        + 0.20 * flow_evidence
        + 0.25 * semantic
        + (0.10 if standing else 0.0)
    )
    reasons: list[str] = []
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    if chain_evidence >= 0.75:
        reasons.append(f"زنجیرهی شناخته ({str(int(chain_evidence * 100)).translate(fa)}٪ موفقیت تاریخی)")
    if flow_evidence > 0:
        reasons.append("جریان واقعی این زنجیره قبلا فایر شده")
    if semantic >= 0.3:
        reasons.append("واژگان جمله با قابلیتها همپوشانی دارند")
    if standing:
        reasons.append("زنجیرهی استاندارد اپراتور")
    return ScoredRoute(
        route=route, score=round(score, 4),
        chain_evidence=round(chain_evidence, 4),
        flow_evidence=round(flow_evidence, 4),
        semantic=round(semantic, 4),
        standing=standing,
        reasons_fa=tuple(reasons),
    )


def rank_routes(routes: list[tuple[str, ...]], command: str) -> list[ScoredRoute]:
    """Rank every acceptable ordering; the best runs first."""
    if not routes:
        return []
    scored = [score_route(r, command) for r in routes]
    return sorted(scored, key=lambda s: s.score, reverse=True)


def scored_fa(scored: ScoredRoute) -> str:
    """The WHY, in fluent Persian."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    pct = str(round(scored.score * 100)).translate(fa)
    route_fa = " → ".join(scored.route)
    why = "؛ ".join(scored.reasons_fa) if scored.reasons_fa else "شواهد کم — با احتیاط اجرا میشود"
    return f"🏆 {route_fa} — امتیاز {pct}٪ ({why})"


__all__ = ["ScoredRoute", "score_route", "rank_routes", "scored_fa"]