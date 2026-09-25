"""The tick pulse — the platform's own heartbeat history.

R44 item 13: ``tick_health`` only ever knew "now" (is there a run in the last
25 hours?). The operator's real question is longer: «چند روز است زنده؟» —
how many days in a row has this mind actually been awake, and which days did
it go silent?

The pulse is DERIVED from run_history, never stored twice: every real run is
already a heartbeat, so a second table would be duplicate state that can only
disagree with the truth. Day boundaries are LOCAL (the operator's day), not
UTC — the same lesson that made «امروز» lie every morning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

WINDOW_DAYS = 7


@dataclass(frozen=True)
class PulseDay:
    """One local day of the platform's life."""

    day: str
    runs: int
    ok: int

    @property
    def awake(self) -> bool:
        return self.runs > 0


def _store() -> Any:
    from universal_mind.database_suite import DatabaseSuite

    return DatabaseSuite(persistent=True)


def pulse_window(days: int = WINDOW_DAYS, *, db: Any | None = None) -> list[PulseDay]:
    """The last `days` LOCAL days, each with its real run count (oldest first).

    One grouped query; days with no runs come back as zeros rather than being
    missing, because a silent day is the signal the operator needs to see.
    """
    store = db if db is not None else _store()
    q = store.query(
        "SELECT date(created_at, 'localtime') AS d, COUNT(*) AS n, "
        "COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
        "WHERE date(created_at, 'localtime') >= date('now', 'localtime', ?) "
        "GROUP BY d",
        (f"-{days - 1} day",),
    )
    seen: dict[str, tuple[int, int]] = {}
    if q.get("ok"):
        for row in q.get("rows", []):
            try:
                seen[str(row["d"])] = (int(row["n"]), int(row["ok_n"]))
            except (TypeError, ValueError, KeyError):
                continue
    today = date.today()
    out: list[PulseDay] = []
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        runs, ok = seen.get(day, (0, 0))
        out.append(PulseDay(day=day, runs=runs, ok=ok))
    return out


def alive_streak(window: list[PulseDay]) -> int:
    """Consecutive awake days ending TODAY (an empty today still counts the run).

    A day in progress with no run yet must not break a real streak: the
    platform is not "dead" at 09:00 because nothing happened since midnight.
    So today is skipped if it is empty, and the streak is counted backwards
    from the newest awake day.
    """
    days = list(reversed(window))
    if not days:
        return 0
    idx = 0
    if not days[0].awake:
        idx = 1  # today has not happened yet; the streak is still alive
    streak = 0
    for d in days[idx:]:
        if not d.awake:
            break
        streak += 1
    return streak


def silent_days(window: list[PulseDay]) -> list[str]:
    """The days in the window with no run at all (a real gap in the pulse)."""
    return [d.day for d in window if not d.awake]


def pulse_report(*, db: Any | None = None) -> dict[str, Any]:
    """The honest heartbeat answer: streak, silence, and the days themselves."""
    window = pulse_window(db=db)
    streak = alive_streak(window)
    silent = silent_days(window)
    return {
        "ok": True,
        "window_days": len(window),
        "streak": streak,
        "silent": silent,
        "days": [
            {"day": d.day, "runs": d.runs, "ok": d.ok, "awake": d.awake} for d in window
        ],
        "error": "",
    }


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n: Any) -> str:
    return str(n).translate(_FA_DIGITS)


def pulse_sentence(report: dict[str, Any]) -> str:
    """The Persian answer to «چند روز است زنده؟» — honest about silence."""
    streak = int(report.get("streak") or 0)
    silent: list[str] = list(report.get("silent") or [])
    days: list[dict[str, Any]] = list(report.get("days") or [])
    today_runs = days[-1]["runs"] if days else 0

    if streak == 0:
        base = "امروز و دیروز نشانی از کار ندارم — تپش قطع است."
    elif streak == 1:
        base = f"۱ روز است زندهام (امروز {_fa(today_runs)} فرمان)."
    else:
        base = f"{_fa(streak)} روز پیوسته زندهام (امروز {_fa(today_runs)} فرمان)."

    if silent:
        named = "، ".join(silent)
        return f"{base} در این هفته {_fa(len(silent))} روز سکوت داشتم: {named}."
    return base



