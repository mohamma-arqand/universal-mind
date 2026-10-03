"""Operator preferences — the platform REMEMBERS what THIS operator likes.

«همیشه نمودار میله‌ای دوست دارم» — a spoken preference, stored once,
applied to every future chart. The system stops being generic: it adapts
to the person talking to it.

Storage: the persistent `operator_preferences` table (key, value, updated_at)
in the same durable mind.db. Rules:
  - set(key, value)  — upsert, stamps time
  - get(key)          — the stored value or None (absence is honest)
  - apply_to(capability, params) — merges known preference keys (chart kind,
    pdf title style, ...) into a params dict WITHOUT overwriting anything
    the command itself said (explicit intent always wins).
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

# preference key -> which capability's param it shapes
_PREFERENCE_SHAPES: dict[str, tuple[str, str]] = {
    # "chart_kind" preference -> capability "chart", param "operation"
    "chart_kind": ("chart", "operation"),
    # R62 T4 — speech accessibility: the remembered SAPI rate
    # (-10..10) shapes every spoken run («کندتر حرف بزن» sets it once).
    "speech_rate": ("speech", "rate"),
}


def _db() -> DatabaseSuite:
    db = DatabaseSuite(persistent=True)
    db.execute(
        "CREATE TABLE IF NOT EXISTS operator_preferences ("
        "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return db


def set(key: str, value: str) -> None:  # noqa: A002 — dict-style API
    # DatabaseSuite.execute takes NO bound params (its API is sql-only) —
    # escape by doubling single quotes, the same contract agent_loop uses.
    k = key.replace("'", "''")
    v = value.replace("'", "''")
    db = _db()
    db.execute(
        f"INSERT INTO operator_preferences (key, value, updated_at) "
        f"VALUES ('{k}', '{v}', CURRENT_TIMESTAMP) "
        f"ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
        f"updated_at = CURRENT_TIMESTAMP"
    )


def get(key: str) -> str | None:
    """The stored preference or None — absence is honest, never a default."""
    db = _db()
    q = db.query("SELECT value FROM operator_preferences WHERE key = ?", (key,))
    rows = q.get("rows", []) if q.get("ok") else []
    if not rows:
        return None
    v = rows[0].get("value")
    return str(v) if v is not None else None


def all_prefs() -> dict[str, str]:
    """R60 Q5 — every stored preference, newest first, read-only.

    «تنظیماتت را نشان بده» — the operator's OWN settings listed from the
    real store. A secret-looking KEY is masked (a preference named like a
    token is not shown aloud); the COUNT is honest either way.
    """
    import re as _re

    secret_key = _re.compile(r"(key|token|secret|password|credential|api)",
                             _re.IGNORECASE)
    db = _db()
    q = db.query(
        "SELECT key, value FROM operator_preferences "
        "ORDER BY updated_at DESC, key"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    out: dict[str, str] = {}
    for row in rows:
        k = str(row.get("key", ""))
        v = str(row.get("value", ""))
        if k and (secret_key.search(k) or len(v) > 120):
            out[k] = "(مخفی — به نظر راز می‌رسد)"
        else:
            out[k] = v
    return out


def apply_to(capability_params: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Merge remembered preferences into the planned params — the command's
    OWN words always win (a preference never overrides an explicit intent).

    Returns a NEW dict; the input is never mutated.
    """
    merged = {cap: dict(p) for cap, p in capability_params.items()}
    for pref_key, (cap, param) in _PREFERENCE_SHAPES.items():
        stored = get(pref_key)
        if stored is None:
            continue
        current = merged.get(cap)
        if current is None:
            continue
        if current.get("kind_explicit"):
            continue  # the operator NAMED the kind this time — explicit wins
        # Without the explicit flag, a bare "line" is the extractor's
        # DEFAULT, not the operator's intent — the preference replaces it.
        merged[cap] = {**current, param: stored}
    return merged


def parse_preference(command: str) -> tuple[str, str] | None:
    """«همیشه نمودار میله‌ای دوست دارم» / «تنظیمات نمودار را تغییر بده به خطی».

    A tiny honest parser: only the shapes we actually apply. None = not a
    preference statement (most sentences are not).
    """
    # R66 P6 — «تنظیمات نمودار را تغییر بده به خطی»: a SETTINGS-CHANGE
    # sentence is a preference statement too (the operator is naming
    # what future charts should look like — not asking to draw one).
    _settings_change = (
        ("تنظیمات" in command or "تنظیم" in command or "پیشفرض" in command or "پیش‌فرض" in command)
        and ("تغییر" in command or "عوض" in command or "بده" in command)
    )
    if "همیشه" not in command and not _settings_change:
        return None
    if "نمودار" in command or "چارت" in command:
        for word, kind in (("دایرهای", "pie"), ("دایره", "pie"),
                           ("میلهای", "bar"), ("میله", "bar"), ("ستونی", "bar"),
                           ("خطی", "line"), ("پراکنده", "scatter"), ("هیستوگرام", "histogram")):
            if word in command:
                return ("chart_kind", kind)
    return None


def remember_from_command(command: str) -> bool:
    """If the command STATES a preference, store it. True when stored."""
    parsed = parse_preference(command)
    if parsed is None:
        return False
    key, value = parsed
    set(key, value)
    return True


__all__ = ["set", "get", "apply_to", "parse_preference", "remember_from_command"]