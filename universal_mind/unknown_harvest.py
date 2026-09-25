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


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("unknown_terms", [
        "CREATE TABLE IF NOT EXISTS unknown_terms ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "term TEXT NOT NULL, hits INTEGER NOT NULL DEFAULT 1, "
        "first_seen TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), "
        "last_seen TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def harvest_unknown(unknown_words: list[str], *, db: DatabaseSuite | None = None) -> int:
    """Record the unknown words of ONE refusal. Returns rows touched."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    touched = 0
    for raw in unknown_words:
        for term in str(raw).split():
            term = term.strip(".,،؛:؟!()«»\"'").strip()
            if not term or len(term) < 2 or term in _STOP:
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
