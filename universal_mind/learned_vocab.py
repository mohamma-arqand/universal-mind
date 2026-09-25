"""The learned vocabulary — the operator TEACHES the platform new words.

R46 item 9: a vocabulary that only changes with a code commit is a
dictionary, not a learner. «واژهی زرشک یعنی دیتا» stores word→capability
in `learned_vocab`; the NEXT command routes correctly with no commit —
the overlay is read BEFORE the static _VOCAB in every route() call.

«چه یاد گرفتی؟» lists what has been taught. Redefinition overwrites.
"""

from __future__ import annotations

import re
from typing import Any

from universal_mind.database_suite import DatabaseSuite

# «واژهی X یعنی Y» / «X یعنی Y» shapes (kept raw).
_DEFINE_RE = re.compile(
    r"(?:واژها?ی\s+)?(?P<word>[\w\u0600-\u06FF]+)\s+یعنی\s+(?P<cap>[\w\u0600-\u06FF]+)"
)

# The operator's word for a capability → the capability name.
_CAP_WORDS = {
    "دیتا": "data", "داده": "data", "دادهها": "data",
    "نمودار": "chart", "چارت": "chart", "نموداره": "chart",
    "پیشبینی": "predict", "پیشگویی": "predict",
    "گزارش": "pdf", "سند": "pdf", "پی دی اف": "pdf",
    "اکسل": "excel", "جدول": "excel",
    "تصویر": "image", "عکس": "image",
    "ایمیل": "email", "نامه": "email",
    "گفتار": "tts", "صدا": "tts",
    "بایگانی": "archive", "زیپ": "archive",
}


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("learned_vocab", [
        "CREATE TABLE IF NOT EXISTS learned_vocab ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "word TEXT NOT NULL UNIQUE, capability TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def parse_definition(command: str) -> dict[str, str] | None:
    """«واژهی X یعنی Y» → {word, cap} (None = not a definition)."""
    m = _DEFINE_RE.search(command)
    if not m:
        return None
    word = m.group("word").strip()
    cap_raw = m.group("cap").strip().rstrip(".,،؛:؟!")
    if word in ("واژه", "واژهی", "که"):
        return None
    return {"word": word, "cap": cap_raw}


def teach(word: str, capability: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Store word→capability (redefinition overwrites, honestly)."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    word = word.strip()
    capability = capability.strip()
    if not word or not capability:
        return {"ok": False, "error": "تعریفِ ناقص"}
    cap = _CAP_WORDS.get(capability, capability)
    esc = word.replace("'", "''")
    store.execute(f"DELETE FROM learned_vocab WHERE word = '{esc}'")
    store.insert_many("learned_vocab", [{"word": word, "capability": cap}])
    return {"ok": True, "error": "", "word": word, "capability": cap}


def learned_words(*, db: DatabaseSuite | None = None) -> list[dict[str, str]]:
    """Everything the operator taught, newest first."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query("SELECT word, capability FROM learned_vocab ORDER BY id DESC")
    rows = q.get("rows", []) if q.get("ok") else []
    return [{"word": str(r["word"]), "capability": str(r["capability"])} for r in rows]


def overlay(db: DatabaseSuite | None = None) -> dict[str, str]:
    """word→capability overlay for route() — {} when nothing is taught."""
    return {d["word"]: d["capability"] for d in learned_words(db=db)}


__all__ = ["ensure_table", "learned_words", "overlay", "parse_definition", "teach"]
