"""Persistent chat history — the conversation survives the window.

The chat tab was UI-only: close the window and the conversation died while
run_history kept only the command/route skeleton. A REAL conversation is what
was SAID — both sides. This module persists every chat message (who, text,
verdict) and replays the newest N on the next opening.

One row per message, written once. Replay never re-inserts.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite


def _db() -> DatabaseSuite:
    return DatabaseSuite.shared_persistent()


def _ensure_table(db: DatabaseSuite) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS chat_history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "who TEXT NOT NULL, "
        "text TEXT NOT NULL, "
        "ok INTEGER DEFAULT 0, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )


def log_message(who: str, text: str, ok: bool = False) -> None:
    """Append ONE chat message (who: من/سیستم/خطا). Never raises."""
    try:
        db = _db()
        _ensure_table(db)
        who_esc = who.replace("'", "''")
        text_esc = text.replace("'", "''")
        db.execute(
            f"INSERT INTO chat_history (who, text, ok) "
            f"VALUES ('{who_esc}', '{text_esc}', {1 if ok else 0})"
        )
    except Exception:  # noqa: BLE001 — the chat never dies over a log failure
        pass


def recent_messages(limit: int = 50) -> list[dict[str, Any]]:
    """The newest N messages, oldest first (chat replay order)."""
    try:
        db = _db()
        _ensure_table(db)
        q = db.query(
            f"SELECT who, text, ok FROM chat_history "
            f"ORDER BY id DESC LIMIT {int(limit)}"
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — replay degrades to empty, honest
        return []
    return [{"who": r["who"], "text": r["text"], "ok": bool(r["ok"])}
            for r in reversed(rows)]


def message_count() -> int:
    """Total persisted messages (a lens, used by probes)."""
    try:
        db = _db()
        _ensure_table(db)
        q = db.query("SELECT COUNT(*) AS n FROM chat_history")
        return int(q["rows"][0]["n"]) if q.get("ok") and q["rows"] else 0
    except Exception:  # noqa: BLE001
        return 0


__all__ = ["log_message", "recent_messages", "message_count"]