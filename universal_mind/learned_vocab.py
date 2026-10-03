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
    "خلاصه": "textsummarize", "خلاصهسازی": "textsummarize",
    "summary": "textsummarize", "summarize": "textsummarize",
}


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("learned_vocab", [
        "CREATE TABLE IF NOT EXISTS learned_vocab ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "word TEXT NOT NULL UNIQUE, capability TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def parse_definition(command: str) -> dict[str, str] | None:
    """«واژهی X یعنی Y» → {word, cap} (None = not a definition).

    R63-P1: only SMALL definition sentences qualify — the pattern must
    span the whole command (a colon-clause sentence like «قابلیت جدید
    یاد بگیر: وقتی گفتم برق رفت یعنی ...» is NOT a word definition;
    grabbing its last «X یعنی Y» poisoned the route overlay with
    word='رفت' → cap='برق' and every «رفت» sentence mis-routed).
    """
    m = _DEFINE_RE.search(command)
    if not m:
        return None
    # the definition must BE the sentence, not a clause inside it
    outside = command.replace(m.group(0), "", 1).strip()
    if outside and not re.fullmatch(r"[.،؛:!?…\"'«»\s]*", outside):
        return None
    word = m.group("word").strip()
    cap_raw = m.group("cap").strip().rstrip(".,،؛:؟!")
    if word in ("واژه", "واژهی", "که", "چیزی", "یکی"):
        return None
    return {"word": word, "cap": cap_raw}


def teach(word: str, capability: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Store word→capability (redefinition overwrites, honestly).

    R63-P1: the capability must be REAL — a known operator word (mapped
    through _CAP_WORDS) or an actual registry capability. Anything else
    is a NAMED refusal, never a silent overlay entry that misroutes
    every later sentence (the live sweep caught word='رفت' → cap='برق'
    slipping through: «command 'unused' is not allowlisted»).
    """
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    word = word.strip()
    capability = capability.strip()
    if not word or not capability:
        return {"ok": False, "error": "تعریفِ ناقص"}
    cap = _CAP_WORDS.get(capability, capability)
    if cap not in _CAP_WORDS.values() and not _is_real_capability(cap):
        known = "، ".join(sorted(set(_CAP_WORDS.values())))
        return {
            "ok": False,
            "error": (
                f"«{capability}» قابلیتی که بشناسم نیست — نمی‌توانم واژه را "
                f"به چیزی ناشناخته وصل کنم. قابلیت‌های شناخته‌شده: {known}."
            ),
        }
    esc = word.replace("'", "''")
    store.execute(f"DELETE FROM learned_vocab WHERE word = '{esc}'")
    store.insert_many("learned_vocab", [{"word": word, "capability": cap}])
    return {"ok": True, "error": "", "word": word, "capability": cap}


def _is_real_capability(cap: str) -> bool:
    """True when `cap` is a capability the registry actually has."""
    try:
        from universal_mind.real_tool_registry import real_tool_registry

        reg = real_tool_registry()
        caps = getattr(reg, "_by_capability", None)
        if isinstance(caps, dict):
            return cap in caps
        names = getattr(reg, "capabilities", None)
        if callable(names):
            return cap in list(names())
    except Exception:  # noqa: BLE001 — the lens never breaks the run
        return False
    return False


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
