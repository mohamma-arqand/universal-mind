"""The weekly letter — the platform writes its own week, unprompted.

R45 item 8: on the first tick of each ISO week the platform renders a real
Persian summary of THAT week (runs, successes, best chain, verdicts, silence)
into a toast the operator actually sees and a `weekly_reports` row the
operator can ask about later («گزارش هفته چطور بود؟»).

Every number is derived from the real store with the LOCAL-day law. A week
with no runs is still written — honestly, as «هفتهای ساکت بود» — because a
fabricated letter is worse than a silent one.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_EXCLUDE = (
    "(outcome_class IS NULL OR outcome_class NOT IN "
    "('blocked_env', 'needs_param', 'unknown_noise'))"
)


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("weekly_reports", [
        "CREATE TABLE IF NOT EXISTS weekly_reports ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "week_start TEXT NOT NULL, report TEXT NOT NULL, "
        "runs INTEGER NOT NULL DEFAULT 0, ok_runs INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def week_letter(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """THIS week's real letter: runs/ok, best chain, verdicts, silence."""
    store = db or DatabaseSuite.shared_persistent()
    q = store.query(
        "SELECT COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
        "WHERE date(created_at, 'localtime') >= date('now', 'localtime', '-6 day') "
        f"AND date(created_at, 'localtime') <= date('now', 'localtime') AND {_EXCLUDE}"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    runs = int(rows[0]["n"]) if rows else 0
    ok = int(rows[0]["ok_n"]) if rows else 0

    best_q = store.query(
        "SELECT route, COUNT(*) AS n FROM run_history "
        "WHERE date(created_at, 'localtime') >= date('now', 'localtime', '-6 day') "
        f"AND succeeded = 1 AND route != '' AND {_EXCLUDE} "
        "GROUP BY route ORDER BY n DESC LIMIT 1"
    )
    best_rows = best_q.get("rows", []) if best_q.get("ok") else []
    best = str(best_rows[0]["route"]) if best_rows else ""

    ensure_table(store)
    try:
        store.execute(
            "CREATE TABLE IF NOT EXISTS operator_verdicts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "command TEXT NOT NULL, route TEXT NOT NULL, "
            "verdict TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        v_q = store.query(
            "SELECT COUNT(*) AS n FROM operator_verdicts "
            "WHERE date(created_at, 'localtime') >= date('now', 'localtime', '-6 day')"
        )
        v_rows = v_q.get("rows", []) if v_q.get("ok") else []
        verdicts = int(v_rows[0]["n"]) if v_rows else 0
    except Exception:  # noqa: BLE001 — verdicts are a lens, never fatal
        verdicts = 0

    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    week_start = monday.isoformat()

    if runs == 0:
        letter = (
            f"نامهی هفته ({_fa(week_start)}): هفتهای ساکت بود — هیچ فرمانی اجرا نشد. "
            "منتظر فرمانهای توایم."
        )
    else:
        rate = round(100 * ok / runs) if runs else 0
        letter = (
            f"نامهی هفته ({_fa(week_start)}): {_fa(runs)} فرمان اجرا کردم؛ "
            f"{_fa(ok)} موفق ({_fa(rate)}٪)"
        )
        if best:
            letter += f"؛ پرکاربردترین مسیر: {best}"
        if verdicts:
            letter += f"؛ {_fa(verdicts)} رأی انسانی ثبت شد"
        letter += "."
    return {
        "ok": True,
        "week_start": week_start,
        "runs": runs,
        "ok_runs": ok,
        "verdicts": verdicts,
        "best_route": best,
        "report": letter,
        "error": "",
    }


def record_weekly_letter(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Render the letter, persist it (one row per week), return it."""
    store = db or DatabaseSuite.shared_persistent()
    info = week_letter(db=store)
    ensure_table(store)
    # one row per week-start: replace this week's letter if re-ticked
    store.insert_many("weekly_reports", [{
        "week_start": info["week_start"],
        "report": info["report"],
        "runs": str(info["runs"]),
        "ok_runs": str(info["ok_runs"]),
    }])
    return info


def due_this_week(*, db: DatabaseSuite | None = None) -> bool:
    """True until this ISO week has its letter row (the tick fires weekly)."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    q = store.query(
        "SELECT COUNT(*) AS n FROM weekly_reports WHERE week_start = ?",
        (monday.isoformat(),),
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return (int(rows[0]["n"]) if rows else 0) == 0


def latest_letter(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """The newest stored letter — «گزارش هفته چطور بود؟» reads THIS."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT week_start, report FROM weekly_reports ORDER BY id DESC LIMIT 1"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    if not rows:
        return {"ok": False, "report": "", "week_start": "", "error": "هنوز نامهای نیست"}
    return {
        "ok": True,
        "report": str(rows[0]["report"]),
        "week_start": str(rows[0]["week_start"]),
        "error": "",
    }
