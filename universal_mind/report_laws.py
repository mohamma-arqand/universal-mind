"""Report laws — the operator's 👍 becomes a drift contract, by name.

R46 item 3: a 👍 is the strongest signal the platform has — until now it
only moved a counter. This module turns each approved command into a
LAW: the real report's distinctive Persian promises (its top report
lines, minus boilerplate) are captured AT VERDICT TIME and stored in
`report_laws` (command → must_contain anchors). check_report_drift then
runs every earned law through the live router alongside the golden
corpus — a regression on a command the operator explicitly liked turns
the gate RED BY NAME.

Storage: one row per (command), refreshed on each new 👍. Cap: 5 anchors
per law, 50 laws — advice is a contract, not a lawsuit.
"""

from __future__ import annotations

import json
from typing import Any

from universal_mind.database_suite import DatabaseSuite

# Lines that carry no promise (pure ceremony, true for any run).
_BOILERPLATE = (
    "✅ اجرا انجام شد", "🏛 داوری ARETĒ", "🔗", "⚖", "🛡", "زمان:", "⏱",
)


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("report_laws", [
        "CREATE TABLE IF NOT EXISTS report_laws ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT NOT NULL, anchors TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])
    db.ensure_schema("run_reports", [
        "CREATE TABLE IF NOT EXISTS run_reports ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT NOT NULL, report TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def keep_report(command: str, report: str, *, db: DatabaseSuite | None = None) -> None:
    """The newest full report per command — what a 👍 later turns into law."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    store.execute(f"DELETE FROM run_reports WHERE command = '{command.replace(chr(39), chr(39)*2)}'")
    store.insert_many("run_reports", [{
        "command": command, "report": str(report)[:2000],
    }])


def last_report(command: str, *, db: DatabaseSuite | None = None) -> str:
    """The stored full report of a command ('' = none, honest)."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT report FROM run_reports WHERE command = ? ORDER BY id DESC LIMIT 1",
        (command,),
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return str(rows[0]["report"]) if rows else ""


def _anchors_from_report(report: str, cap: int = 5) -> list[str]:
    """The distinctive promise lines of a real report (no boilerplate)."""
    anchors: list[str] = []
    for line in str(report).splitlines():
        line = line.strip()
        if not line or any(b in line for b in _BOILERPLATE):
            continue
        # a promise line names a real artifact/number/answer — keep it
        anchors.append(line[:60])
        if len(anchors) >= cap:
            break
    return anchors


def record_law(command: str, report: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Turn ONE 👍 into (or refresh) a law. Returns the stored anchors."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    cmd = command.strip()
    anchors = _anchors_from_report(report)
    if not cmd or not anchors:
        return {"ok": False, "anchors": [], "error": "قانونِ خالی — گزارشِ وعدهی نداشت"}
    store.execute(f"DELETE FROM report_laws WHERE command = '{cmd.replace(chr(39), chr(39)*2)}'")
    store.insert_many("report_laws", [{
        "command": cmd,
        "anchors": json.dumps(anchors, ensure_ascii=False),
    }])
    return {"ok": True, "anchors": anchors, "error": ""}


def learned_laws(limit: int = 50, *, db: DatabaseSuite | None = None) -> list[tuple[str, dict[str, list[str]]]]:
    """The stored laws, in the golden-corpus shape the drift gate runs."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        f"SELECT command, anchors FROM report_laws ORDER BY id DESC LIMIT {int(limit)}"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    out: list[tuple[str, dict[str, list[str]]]] = []
    for r in rows:
        try:
            anchors = list(json.loads(str(r["anchors"]) or "[]"))
        except (ValueError, TypeError):
            continue
        if not anchors:
            continue
        out.append((str(r["command"]), {"must_contain": anchors, "must_not_contain": []}))
    return out


__all__ = ["ensure_table", "keep_report", "last_report", "learned_laws", "record_law"]
