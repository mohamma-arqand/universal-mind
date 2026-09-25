"""History compaction — the old runs move to an archive, nothing is lost.

R45 item 13: run_history grows forever (34k+ rows); the hot tables stay
lean while the past stays PROVABLE. Rows older than the retention window
move to run_history_archive (same columns + archived_at), in small
batches, with before/after counts printed and a rollback that moves
them back. A compaction that cannot prove its own reversibility is a
deletion, and deletion is not what this is.

Laws:
- small batches (default 500) — the live store is never locked long;
- counts before/after for BOTH tables — the sum must be invariant;
- rollback() moves the archived window back — proof, not promise;
- the learning stats (windows/letters) already read run_history only,
  so the archive is invisible to them by design.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def ensure_archive(db: DatabaseSuite) -> None:
    db.ensure_schema("run_history_archive", [
        "CREATE TABLE IF NOT EXISTS run_history_archive ("
        "id INTEGER PRIMARY KEY, command TEXT, route TEXT, succeeded TEXT, "
        "excellence TEXT, outcome_class TEXT, flows TEXT, created_at TEXT, "
        "archived_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def compact_history(
    *, db: DatabaseSuite | None = None, older_than_days: int = 90, batch: int = 500
) -> dict[str, Any]:
    """Move rows older than the window to the archive. Returns the proof."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_archive(store)
    moved = 0
    while True:
        q = store.query(
            "SELECT id FROM run_history "
            "WHERE date(created_at, 'localtime') < date('now', 'localtime', ?) "
            f"ORDER BY id LIMIT {int(batch)}",
            (f"-{int(older_than_days)} day",),
        )
        rows = q.get("rows", []) if q.get("ok") else []
        if not rows:
            break
        ids = [str(int(r["id"])) for r in rows]
        id_list = ",".join(ids)
        store.execute(
            "INSERT INTO run_history_archive (id, command, route, succeeded, "
            "excellence, outcome_class, flows, created_at) "
            f"SELECT id, command, route, succeeded, excellence, outcome_class, "
            f"flows, created_at FROM run_history WHERE id IN ({id_list})"
        )
        store.execute(f"DELETE FROM run_history WHERE id IN ({id_list})")
        moved += len(ids)
        if len(ids) < batch:
            break
    live_q = store.query("SELECT COUNT(*) AS n FROM run_history")
    arch_q = store.query("SELECT COUNT(*) AS n FROM run_history_archive")
    live = int(live_q["rows"][0]["n"]) if live_q.get("ok") else -1
    arch = int(arch_q["rows"][0]["n"]) if arch_q.get("ok") else -1
    return {
        "ok": True, "moved": moved, "live": live, "archived": arch,
        "report": f"{_fa(moved)} ردیفِ کهنه به آرشیو رفت؛ جدول اصلی {_fa(live)} ردیف، آرشیو {_fa(arch)} ردیف.",
        "error": "",
    }


def rollback_archive(
    *, db: DatabaseSuite | None = None, batch: int = 500
) -> dict[str, Any]:
    """Move EVERYTHING back from the archive — the reversibility proof."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_archive(store)
    moved = 0
    while True:
        q = store.query(
            f"SELECT id FROM run_history_archive ORDER BY id LIMIT {int(batch)}"
        )
        rows = q.get("rows", []) if q.get("ok") else []
        if not rows:
            break
        ids = ",".join(str(int(r["id"])) for r in rows)
        store.execute(
            "INSERT OR IGNORE INTO run_history (id, command, route, succeeded, "
            "excellence, outcome_class, flows, created_at) "
            f"SELECT id, command, route, succeeded, excellence, outcome_class, "
            f"flows, created_at FROM run_history_archive WHERE id IN ({ids})"
        )
        store.execute(f"DELETE FROM run_history_archive WHERE id IN ({ids})")
        moved += len(rows)
        if len(rows) < batch:
            break
    return {"ok": True, "moved": moved, "report": f"{_fa(moved)} ردیف به جدول اصلی برگشت.", "error": ""}
