"""Named memory — «یادت باشد» / «یادم باشه» (R46 item 4).

Until now every remembered fact lived only in hidden tables. The
operator's natural way of MAKING a memory — «یادت باشد فردا ساعت ۱۰
یادم کن که جلسه دارم» or «یادت باشد اسم شریک من زهراست» — went to the
unknown-terms bin. This module is the honest platform answer:

  REMEMBER  → named_memory table (fact, scope, created_at)
  RECALL    → the next matching run's report LEADS with the fact
  FORGET    → «یادت نرود» / «دیگه یادت نره» deletes it honestly

A fact that never surfaces again is hoarding, not memory. Every fact
carries the count of times it has actually been USED (usage_count) —
the advisor can later decide what deserves to stay.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

# The remember/forget phrase shapes, kept raw and honest.
_REMEMBER_MARKERS = ("یادت باشد", "یادم باشه", "یادم باشد", "به یاد داشته باش")


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("named_memory", [
        "CREATE TABLE IF NOT EXISTS named_memory ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "fact TEXT NOT NULL, "
        "scope TEXT NOT NULL DEFAULT 'general', "
        "usage_count INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def parse_remember_request(command: str) -> dict[str, Any] | None:
    """Extract the FACT from a «یادت باشد…» command (None = not one)."""
    text = command.strip()
    lower = text.lower()
    marker = next((m for m in _REMEMBER_MARKERS if m in lower), None)
    if marker is None:
        return None
    rest = text.split(marker, 1)[1].strip(" :،.")
    # R62 T1 — THE MARKER CAN TRAIL THE FACT: «جلسه شنبه ساعت ۱۰ است —
    # یادت باشد» puts the marker AFTER the appointment. With nothing after
    # the marker, the fact is what PRECEDES it (minus the dash/colon noise).
    if not rest:
        before = text.split(marker, 1)[0].strip(" :،.-—")
        if not before:
            return None
        rest = before
    if not rest:
        return None
    # «که» often introduces the actual fact: «یادت باشد که فردا جلسه دارم»
    if rest.startswith("که "):
        rest = rest[3:].strip(" :،.")
    return {"fact": rest, "raw": text}


def save_fact(fact: str, scope: str = "general", *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Store a fact (dedupe by exact text, refresh created_at)."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    fact = fact.strip()
    if not fact:
        return {"ok": False, "error": "حقیقی برای یادداشت نبود"}
    esc = fact.replace("'", "''")
    store.execute(f"DELETE FROM named_memory WHERE fact = '{esc}'")
    store.insert_many("named_memory", [{
        "fact": fact, "scope": scope, "usage_count": 0,
    }])
    return {"ok": True, "error": "", "fact": fact}


def recall_facts(limit: int = 3, *, db: DatabaseSuite | None = None) -> list[dict[str, Any]]:
    """The newest facts (max `limit`), most-used first, for report leading."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT id, fact, scope, usage_count FROM named_memory "
        f"ORDER BY usage_count DESC, id DESC LIMIT {int(limit)}"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return [{"id": int(r["id"]), "fact": str(r["fact"]), "scope": str(r["scope"]),
             "usage_count": int(r["usage_count"])} for r in rows]


def _bump_usage(fact_id: int, *, db: DatabaseSuite | None = None) -> None:
    store = db or DatabaseSuite.shared_persistent()
    store.execute(f"UPDATE named_memory SET usage_count = usage_count + 1 WHERE id = {int(fact_id)}")


def forget_matching(text: str, *, db: DatabaseSuite | None = None) -> list[str]:
    """Delete every fact whose text appears in `text`; returns what's gone."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query("SELECT id, fact FROM named_memory")
    rows = q.get("rows", []) if q.get("ok") else []
    gone: list[str] = []
    for r in rows:
        f = str(r["fact"])
        if f and (f in text or text in f):
            store.execute(f"DELETE FROM named_memory WHERE id = {int(r['id'])}")
            gone.append(f)
    return gone


def surface_for_command(command: str, *, db: DatabaseSuite | None = None) -> tuple[str, list[int]]:
    """The facts relevant to THIS command (subword overlap), with ids.

    Returns ("", []) when nothing matches — absence is honest, no fake
    relevance. A fact surfaces when ≥2 distinctive tokens overlap with
    the command (so «جلسه» alone doesn't drag in every meeting fact).
    """
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query("SELECT id, fact, scope FROM named_memory")
    rows = q.get("rows", []) if q.get("ok") else []
    cmd_tokens = {t for t in _tokenize(command) if len(t) >= 3}
    out: list[tuple[str, int]] = []
    for r in rows:
        fact = str(r["fact"])
        fact_tokens = {t for t in _tokenize(fact) if len(t) >= 3}
        overlap = len(cmd_tokens & fact_tokens)
        if overlap >= 2:
            out.append((fact, int(r["id"])))
    if not out:
        return "", []
    bump_ids = [i for _, i in out]
    for i in bump_ids:
        _bump_usage(i, db=store)
    line = "📌 " + "؛ ".join(f for f, _ in out[:2])
    return line, bump_ids


def _tokenize(text: str) -> set[str]:
    """Very small tokenizer: split on non-letter chars (Persian-aware)."""
    import re

    return {t for t in re.split(r"[^\w\u0600-\u06FF]+", str(text)) if t}


__all__ = [
    "ensure_table", "parse_remember_request", "recall_facts",
    "save_fact", "surface_for_command", "forget_matching",
]
