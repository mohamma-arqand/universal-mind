"""Time windows — the operator's questions about YESTERDAY, WEEKS, MONTHS.

R45 item 1: «امروز» already worked; the operator's real questions reach
further back («دیروز چی کار کردی؟», «این هفته چطور بود؟»). One module, three
windows, the same LOCAL-day law (a UTC stamp is converted before comparison —
the bug that made «امروز» lie every morning). Day boundaries are LOCAL, runs
that were honest environment-refusals never count, and silence is reported as
silence — never fabricated work and never a hidden gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

WINDOWS: tuple[tuple[str, str], ...] = (
    ("امروز", "0 day"),
    ("دیروز", "-1 day"),
    ("این هفته", "-6 day"),
    ("هفته پیش", "-13 day"),
    ("این ماه", "-29 day"),
    ("ماه پیش", "-59 day"),
)

_EXCLUDE = (
    "(outcome_class IS NULL OR outcome_class NOT IN "
    "('blocked_env', 'needs_param', 'unknown_noise'))"
)


@dataclass(frozen=True)
class WindowStats:
    """One named window's real counts."""

    name: str
    runs: int
    ok: int

    @property
    def rate(self) -> int:
        return round(100 * self.ok / self.runs) if self.runs else 0


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def window_stats(name: str, *, db: Any) -> WindowStats:
    """The real (runs, ok) of one named window, LOCAL-day law, refusals excluded."""
    modifiers = dict(WINDOWS)
    mod = modifiers.get(name)
    if mod is None:
        raise ValueError(f"پنجرهی ناشناخته: {name}")
    if name in ("این هفته", "هفته پیش", "این ماه", "ماه پیش"):
        # a RANGE: from the boundary day to the end of the window
        end_mod = {"این هفته": "0 day", "هفته پیش": "-7 day",
                   "این ماه": "0 day", "ماه پیش": "-30 day"}[name]
        q = db.query(
            "SELECT COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
            "WHERE date(created_at) >= date('now', 'localtime', ?) "
            f"AND date(created_at) <= date('now', 'localtime', ?) AND {_EXCLUDE}",
            (mod, end_mod),
        )
    else:
        q = db.query(
            "SELECT COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
            f"WHERE date(created_at) = date('now', 'localtime', ?) AND {_EXCLUDE}",
            (mod,),
        )
    rows = q.get("rows", []) if q.get("ok") else []
    n = int(rows[0]["n"]) if rows else 0
    ok_n = int(rows[0]["ok_n"]) if rows else 0
    return WindowStats(name=name, runs=n, ok=ok_n)


def window_sentence(name: str, *, db: Any) -> str:
    """The honest Persian answer for one window — silence says so."""
    s = window_stats(name, db=db)
    if s.runs == 0:
        return f"{name} نشانی از کار ندارم — سکوت بود."
    return (
        f"{name} {_fa(s.runs)} فرمان اجرا کردم؛ {_fa(s.ok)} موفق ({_fa(s.rate)}٪)."
    )
