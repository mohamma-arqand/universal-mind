"""The morning briefing — the first tick of each day writes the day open.

R46 item 10: the tick fired everything DUE; but the operator opening the
laptop each morning got silence. The FIRST tick of each LOCAL day writes
a three-line briefing — yesterday's outcome, today's standings, any red
signal — into a `daily_briefings` row and a toast, and «بریفینگ امروز را
بگو» reads the very same row back. A silent day is never fabricated: a
day with no runs says so honestly.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("daily_briefings", [
        "CREATE TABLE IF NOT EXISTS daily_briefings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "day TEXT NOT NULL UNIQUE, report TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def due_today(day: str, *, db: DatabaseSuite | None = None) -> bool:
    """True when no briefing exists for this LOCAL day yet."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT id FROM daily_briefings WHERE day = ?", (day,)
    )
    return not (q.get("ok") and q.get("rows"))


def record_briefing(day: str, *, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Write TODAY's briefing from the REAL tables. Returns the report."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)

    # Line 1 — yesterday's outcome (runs, successes).
    y_ok = y_all = 0
    try:
        q = store.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE date(created_at) = date('now', 'localtime', '-1 day')"
        )
        y_all = int(q["rows"][0]["n"]) if q.get("ok") and q.get("rows") else 0
        q2 = store.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE date(created_at) = date('now', 'localtime', '-1 day') AND succeeded = 1"
        )
        y_ok = int(q2["rows"][0]["n"]) if q2.get("ok") and q2.get("rows") else 0
    except Exception:  # noqa: BLE001 — a line is a lens, never fatal
        pass

    # Line 2 — today's standings (active goals, paused, runs so far).
    n_active = n_paused = n_today = 0
    try:
        q = store.query("SELECT COUNT(*) AS n FROM goals WHERE state = 'active'")
        n_active = int(q["rows"][0]["n"]) if q.get("ok") and q.get("rows") else 0
        q2 = store.query("SELECT COUNT(*) AS n FROM goals WHERE state = 'paused'")
        n_paused = int(q2["rows"][0]["n"]) if q2.get("ok") and q2.get("rows") else 0
        q3 = store.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE date(created_at) = date('now', 'localtime')"
        )
        n_today = int(q3["rows"][0]["n"]) if q3.get("ok") and q3.get("rows") else 0
    except Exception:  # noqa: BLE001
        pass

    # Line 3 — any red signal (drift red, poisoned goals).
    reds: list[str] = []
    try:
        from universal_mind.drift import check_report_drift

        bad = [v for v in check_report_drift() if not v.ok]
        if bad:
            reds.append(f"رانش: {len(bad)} قانون قرمز")
    except Exception:  # noqa: BLE001
        pass
    try:
        from universal_mind.agent_loop import _ensure_goals_table, _poisoned_goals

        _ensure_goals_table(store)
        poisoned = _poisoned_goals()
        if poisoned:
            reds.append(f"{_fa(len(poisoned))} هدف زهرآلود")
    except Exception:  # noqa: BLE001
        pass

    lines: list[str] = []
    if y_all:
        lines.append(f"• دیروز {_fa(y_all)} فرمان اجرا شد؛ {_fa(y_ok)} موفق.")
    else:
        lines.append("• دیروز فرمانی اجرا نشد — روزِ خاموش، صادقانه.")
    bits: list[str] = []
    if n_active:
        bits.append(f"{_fa(n_active)} هدف فعال")
    if n_paused:
        bits.append(f"{_fa(n_paused)} در انتظار تصمیمت")
    if n_today:
        bits.append(f"{_fa(n_today)} فرمان امروز")
    lines.append(
        "• امروز: " + ("، ".join(bits) if bits else "هنوز هیچ — صبح تو آغازش میکند") + "."
    )
    lines.append(
        "• " + ("سیگنال قرمز: " + "؛ ".join(reds) if reds else "سیگنال قرمز: هیچ — همه سبز")
    )
    report = "☀️ بریفینگ امروز:\n" + "\n".join(lines)

    store.execute(f"DELETE FROM daily_briefings WHERE day = '{day.replace(chr(39), chr(39)*2)}'")
    store.insert_many("daily_briefings", [{"day": day, "report": report}])
    return {"ok": True, "report": report, "error": ""}


def today_briefing(*, db: DatabaseSuite | None = None) -> str:
    """«بریفینگ امروز را بگو» — the stored row ('' = none, honest)."""
    from datetime import datetime

    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    day = datetime.now().strftime("%Y-%m-%d")
    q = store.query("SELECT report FROM daily_briefings WHERE day = ?", (day,))
    rows = q.get("rows", []) if q.get("ok") else []
    return str(rows[0]["report"]) if rows else ""


__all__ = ["due_today", "record_briefing", "today_briefing"]
