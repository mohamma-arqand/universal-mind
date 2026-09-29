"""Conversation memory — the LAST context feeds the NEXT command.

«و حالا نمودارش را بکش» after «میانگین ۵ و ۷ را حساب کن» must know WHAT
"it" is. Real conversation carries pronouns; a memoryless router drops them.

This module keeps a small `last_context` row (the newest successful run's
command, route, and its key output) in the persistent store, and answers
one question: does THIS command REFER to it? A reference is a bare pronoun
or an anaphora marker («نمودارش»، «همان»، «همین»، «اشاره»، «بکشش») — the
command names an ACTION but no SUBJECT of its own.

The rule (same family as every explicit-intent law here): a command that
names its own subject never takes the context; a bare reference does —
and only when there IS a real last context (absence is honest, never
invented).
"""

from __future__ import annotations

import re
from typing import Any

from universal_mind.database_suite import DatabaseSuite

# Anaphora markers: the command speaks OF the previous thing.
# Retention: the table is a sliding window, never a ledger.
KEEP_ROWS = 50

# Anaphora markers. The possessive «ش» (it) on an ACTION verb is the signal
# («نمودارش»، «تحلیلش»، «بفرستش»، «بخوانش») — but that suffix is a false
# positive inside compound words («خورش»), so the RE alone is not enough;
# refers_to_last() also fires for an action-only command when there IS a real
# prior context, because by the time routing reached memory a capability-less
# command is the conversation's continuation, not smalltalk (the smalltalk /
# status / continue classes return earlier).
_POSSESSIVE_ACTION_RE = re.compile(
    r"(نمودارش|حسابش|گزارشش|بکشش|ذخیرهاش|بخوانش|تحلیلش|بیاورش|بفرستش|بگیرش|"
    r"بسازش|چاپش|همان|همین|اشاره|قبلی|آن|پارسالش)"
)


def save_context(command: str, route: list[str], result: dict[str, Any]) -> None:
    """Persist the newest successful run as the conversation's last context.

    R41: the table is a WINDOW, not a ledger — only the newest KEEP rows
    survive (retention GC on every write). Unbounded growth (caught live:
    3,838 rows when exactly 1 is ever read) wasted the durable store.
    """
    try:
        db = DatabaseSuite.shared_persistent()
    except Exception:  # noqa: BLE001 — the memory is a courtesy, never a crash
        return
    import json as _json

    res = _json.dumps(result, ensure_ascii=False, default=str)[:2000]
    cmd = command.replace("'", "''")
    # ONE transaction: schema + insert + retention GC. Measured live, the three
    # separate execute() calls cost three full connect+commit cycles on the
    # hot path; batching keeps the run inside its latency budget.
    db.execute_many([
        "CREATE TABLE IF NOT EXISTS last_context ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, route TEXT, "
        "result TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        f"INSERT INTO last_context (command, route, result) "
        f"VALUES ('{cmd}', '{','.join(route)}', '{res.replace(chr(39), chr(39) * 2)}')",
        # RETENTION GC: keep the newest window (the newest is what last_context()
        # reads; a small tail is kept for debugging honesty), trim the rest.
        f"DELETE FROM last_context WHERE id <= "
        f"(SELECT MAX(id) - {KEEP_ROWS} FROM last_context)",
    ])


def last_context() -> dict[str, Any] | None:
    """The newest successful context row, or None (absence is honest)."""
    try:
        db = DatabaseSuite.shared_persistent()
    except Exception:  # noqa: BLE001 — the memory is a courtesy, never a crash
        return None
    try:
        q = db.query(
            "SELECT command, route, result FROM last_context ORDER BY id DESC LIMIT 1"
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — the memory is a courtesy
        return None
    if not rows:
        return None
    import json as _json

    try:
        result = _json.loads(rows[0].get("result") or "{}")
    except (ValueError, TypeError):
        result = {}
    return {
        "command": rows[0].get("command", ""),
        "route": [c for c in str(rows[0].get("route", "")).split(",") if c],
        "result": result,
    }


def refers_to_last(command: str) -> bool:
    """Does THIS command speak of the previous thing (an anaphora)?

    Either the possessive marker on an action word («تحلیلش کن»), or — when
    routing has already concluded the command names NO capability — a real
    prior context implies continuation. Absence is still honest: no context,
    no reference.
    """
    return bool(_POSSESSIVE_ACTION_RE.search(command))


def context_params_for(command: str) -> dict[str, Any] | None:
    """The LAST context's route-specific params, when this command refers.

    Returns the previous run's extracted params (the subject it named) so
    the anaphoric command («نمودارش را بکش») reuses the same data — or None
    when there is no context or the command names its own subject.
    """
    if not refers_to_last(command):
        return None
    ctx = last_context()
    if ctx is None or not ctx["route"]:
        return None
    return {
        "route": ctx["route"],
        "command": ctx["command"],
        "result": ctx["result"],
    }


__all__ = ["save_context", "last_context", "refers_to_last", "context_params_for"]