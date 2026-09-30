"""THE INJECTION LEDGER — every time the outside world tried to give orders.

R57 wave-3 taught the platform to SEE an injection in fetched content. An
attempt only seen is an attempt forgotten, so this module keeps the record:
when a fetch comes back with a non-clean quarantine verdict, one row lands in
``injection_attempts`` (url, verdict, the hostile families, how many lines,
when). The operator can then ask «تزریق‌ها را نشان بده» and read the REAL
list back — not a claim that the feature works, the log of it working.

Laws:
  - Recording never breaks a fetch: any store problem is swallowed and the
    fetch result is returned unchanged (a ledger is an observer).
  - ONE CLOCK: ``created_at`` defaults to ``datetime('now','localtime')``,
    never ``CURRENT_TIMESTAMP`` (that default is UTC and every «امروز»-style
    read would silently miss the row).
  - Only a NON-CLEAN verdict is recorded — a clean page is not an event.
Removing rows is a DELETE the operator asks for by name; nothing here
deletes on its own.
"""

from __future__ import annotations

import re
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_TABLE = "injection_attempts"


def _db(db: DatabaseSuite | None = None) -> DatabaseSuite:
    store = db or DatabaseSuite.shared_persistent()
    store.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "url TEXT, "
        "verdict TEXT, "
        "kinds TEXT, "
        "findings_count INTEGER DEFAULT 0, "
        "created_at TEXT DEFAULT (datetime('now','localtime')))"
    )
    return store


def _fa(text: object) -> str:
    """Persian digits — a Latin digit in an operator report is a leak."""
    return str(text).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def record(url: str, quarantine: dict[str, Any], *, db: DatabaseSuite | None = None) -> bool:
    """Persist one injection attempt. True when a row was written.

    Never lets a store failure reach the caller: an observer that breaks the
    thing it observes is worse than no observer.
    """
    try:
        verdict = str(quarantine.get("verdict", "")).strip()
        if verdict in ("", "clean"):
            return False
        kinds = quarantine.get("counts") or {}
        named = ", ".join(f"{k}x{v}" for k, v in sorted(kinds.items()) if v)
        findings = len(quarantine.get("findings") or [])
        store = _db(db)
        safe_url = url.strip()[:500].replace("'", "''")
        store.execute(
            f"INSERT INTO {_TABLE} (url, verdict, kinds, findings_count) VALUES "
            f"('{safe_url}', '{verdict.replace(chr(39), chr(39) * 2)}', "
            f"'{named.replace(chr(39), chr(39) * 2)}', {int(findings)})"
        )
        return True
    except Exception:
        return False


def record_from_fetch(
    url: str, fetch_result: dict[str, Any], *, db: DatabaseSuite | None = None
) -> bool:
    """Record straight from a ``WebFetchTool.fetch`` result."""
    q = fetch_result.get("quarantine")
    if not isinstance(q, dict):
        return False
    return record(url, q, db=db)


def list_attempts(
    *, db: DatabaseSuite | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """The most recent attempts, newest first."""
    try:
        store = _db(db)
        q = store.query(
            f"SELECT url, verdict, kinds, findings_count, created_at FROM {_TABLE} "
            f"ORDER BY id DESC LIMIT {int(limit)}"
        )
        rows = q.get("rows", []) if q.get("ok") else []
        return [
            {
                "url": str(r["url"]),
                "verdict": str(r["verdict"]),
                "kinds": str(r["kinds"]),
                "findings_count": int(r["findings_count"] or 0),
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]
    except Exception:
        return []


def count(*, db: DatabaseSuite | None = None) -> int:
    """How many attempts are on record (0 when the store is unreadable)."""
    try:
        store = _db(db)
        q = store.query(f"SELECT COUNT(*) AS n FROM {_TABLE}")
        rows = q.get("rows", []) if q.get("ok") else []
        return int(rows[0]["n"]) if rows else 0
    except Exception:
        return 0


def _fa_kinds(kinds: str) -> str:
    """«overridex1, exfiltrationx2» → «override×۱، exfiltration×۲».

    The count is parsed with a regex anchored at the END — a blind
    ``"x" → "×"`` replacement mangles a family name that CONTAINS an x
    («e×filtration»), which is exactly the kind of silent corruption a
    rendered report must never ship.
    """
    if not kinds:
        return "نامشخص"
    parts = []
    for chunk in kinds.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)x(\d+)$", chunk)
        if m:
            parts.append(f"{m.group(1)}×{_fa(m.group(2))}")
        else:
            parts.append(chunk)
    return "، ".join(parts) if parts else "نامشخص"


def render_fa(attempts: list[dict[str, Any]] | None = None, *, db: DatabaseSuite | None = None,
              limit: int = 10) -> str:
    """A Persian report of the ledger — the honest read-back.

    EVERY rendered field is Persianized (the date and the family counts too):
    a Latin digit anywhere in the operator's report is a leak, not a detail.
    """
    rows = attempts if attempts is not None else list_attempts(db=db, limit=limit)
    if not rows:
        return (
            "تا حالا هیچ تلاش تزریقی ثبت نشده — هر صفحه‌ای که خوانده شده، "
            "فرمانی در خودش نداشته."
        )
    lines = [f"{_fa(len(rows))} تلاش تزریقی ثبت شده (تازه‌ترین اول):"]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"  {_fa(i)}. [{_fa(r['created_at'])}] {r['url']} — "
            f"حکم: {r['verdict']} — {_fa_kinds(str(r['kinds']))} "
            f"({_fa(r['findings_count'])} بند) — اجرا نشد"
        )
    return "\n".join(lines)


__all__ = [
    "count",
    "list_attempts",
    "record",
    "record_from_fetch",
    "render_fa",
]
