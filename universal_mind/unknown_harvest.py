"""The unknown harvest — what the operator says that the platform misses.

R45 item 12: every honest «این فرمان را نشناختم» is a vocabulary lesson
waiting to be learned. The harvest table (unknown_terms: term, hits,
first_seen, last_seen) is written at the moment of the refusal itself;
the nightly tick reports the week's top unknowns; «چه واژههایی را
نمیشناسی؟» answers in conversation.

Data for the NEXT vocabulary wave — never a dead end again.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_STOP = {"را", "و", "به", "از", "با", "برای", "که", "این", "آن", "هم", "می",
         "کن", "بده", "بساز", "نشان", "بده.", "لطفا", "یک", "دو"}

# R46-7 — REFUSAL-SENTENCE STOPWORDS: the refusal sentence ITSELF is not
# vocabulary. Words that appear in the platform's OWN refusal boilerplate
# («هیچ قابلیتی شناخته نشد — فرمان اجرا نمیکند») were harvested 30 times
# each and drowned the real subject words. Caught live; poisoned rows are
# purged by purge_refusal_noise() and never harvested again.
_REFUSAL_STOP = {
    "فرمان", "هیچ", "قابلیتی", "ندارد", "نمیکند", "نشد", "شناخته",
    "شناختهشد", "میکند", "باشد", "است", "است.", "فعال", "فعال.",
    "گام", "هدف", "هدف:", "رو", "را.", "کنم", "کنی", "کنیم",
}


def purge_refusal_noise(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Delete every poisoned row (refusal-sentence words + bare test junk).

    Returns what was purged and what remains — the honest audit line.
    """
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query("SELECT id, term, hits FROM unknown_terms")
    rows = q.get("rows", []) if q.get("ok") else []
    purged: list[str] = []
    purged_hits = 0
    for r in rows:
        term = str(r["term"])
        if term in _REFUSAL_STOP or term in _STOP or len(term) <= 3 and not term.isalpha():
            purged.append(term)
            purged_hits += int(r["hits"])
            store.execute(f"DELETE FROM unknown_terms WHERE id = {int(r['id'])}")
    return {"purged": purged, "purged_hits": purged_hits,
            "remaining": len(rows) - len(purged)}


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("unknown_terms", [
        "CREATE TABLE IF NOT EXISTS unknown_terms ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "term TEXT NOT NULL, hits INTEGER NOT NULL DEFAULT 1, "
        "first_seen TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), "
        "last_seen TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
        # R46-11 — term is UNIQUE at the index level: a duplicate term can
        # never silently fork into two rows (the harvest upserts by hand;
        # the index is the seatbelt).
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_unknown_term ON unknown_terms (term)",
    ])


def harvest_unknown(unknown_words: list[str], *, db: DatabaseSuite | None = None) -> int:
    """Record the unknown words of ONE refusal. Returns rows touched."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    touched = 0
    for raw in unknown_words:
        for term in str(raw).split():
            term = term.strip(".,،؛:؟!()«»\"'").strip()
            if (not term or len(term) < 2 or term in _STOP
                    or term in _REFUSAL_STOP):
                continue
            q = store.query("SELECT id, hits FROM unknown_terms WHERE term = ?", (term,))
            rows = q.get("rows", []) if q.get("ok") else []
            if rows:
                store.execute(
                    f"UPDATE unknown_terms SET hits = hits + 1, "
                    f"last_seen = datetime('now', 'localtime') WHERE id = {int(rows[0]['id'])}"
                )
            else:
                store.insert_many("unknown_terms", [{"term": term, "hits": "1"}])
            touched += 1
    return touched


def top_unknowns(limit: int = 5, *, db: DatabaseSuite | None = None) -> list[dict[str, Any]]:
    """The most-hit unknown terms — the vocabulary the operator actually lacks."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT term, hits, last_seen FROM unknown_terms "
        "ORDER BY hits DESC, last_seen DESC LIMIT ?",
        (limit,),
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return [
        {"term": str(r["term"]), "hits": int(r["hits"]), "last_seen": str(r["last_seen"])}
        for r in rows
    ]


def unknown_sentence(limit: int = 5, *, db: DatabaseSuite | None = None) -> str:
    """The conversational answer: «چه واژههایی را نمیشناسی؟»."""
    terms = top_unknowns(limit, db=db)
    if not terms:
        return "هنوز واژهی ناشناختهای از تو نگرفتهام — همهی حرفهایت را فهمیدهام."
    parts = [f"«{t['term']}» ({_fa(t['hits'])} بار)" for t in terms]
    return "این واژهها را هنوز نمیشناسم: " + "، ".join(parts) + " — لیستِ موجِ واژگانِ بعدیام."
