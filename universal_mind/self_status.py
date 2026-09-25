"""«وضعیت خودت چطور است؟» — the platform's own multi-signal health answer.

R45 item 10: the operator asks ONE question; the platform answers with
FIVE real signals, each read from its live source (no cache, no guess):

  pulse    — the 7-day streak and silent days (tick_pulse)
  drift    — the hot-path ratio vs the committed baseline (drift)
  backup   — the newest backup's date/size and the last drill's verdict
  verdicts — the human loop: 👍/👎 counts (operator_verdicts)
  red-team — open findings the hostile corpus left behind

An unavailable signal says so («—») instead of being silently dropped:
a health answer that hides a dead gauge is worse than no answer.
"""

from __future__ import annotations

from datetime import datetime
from collections.abc import Callable
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def _pulse_line(db: DatabaseSuite) -> str:
    from universal_mind.tick_pulse import pulse_report

    pr = pulse_report(db=db)
    streak = int(pr.get("streak", 0))
    line = f"تپش: {_fa(streak)} روز پیوسته"
    silent = list(pr.get("silent", []))
    if silent:
        line += f" ({_fa(len(silent))} روز سکوت)"
    return line


def _drift_line() -> str:
    from universal_mind.drift import check_perf_drift

    dv = check_perf_drift()
    return ("رانش کارایی: " + dv.detail) if dv.ok else (f"رانش کارایی: ⚠️ {dv.detail}")


def _backup_line() -> str:
    """The newest backup, named with its real age and size."""
    from universal_mind.restore_drill import _newest_backup

    store_dir = DatabaseSuite.DEFAULT_DB_DIR
    nb = _newest_backup(store_dir)
    if nb is None:
        return "بکاپ: هنوز هیچ بکاپی ساخته نشده"
    stat = nb.stat()
    age_days = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
    mb = stat.st_size / (1024 * 1024)
    return f"بکاپ: {_fa(age_days)} روز پیش، {_fa(round(mb))} مگابایت ({nb.name})"


def _verdict_line(db: DatabaseSuite) -> str:
    db.execute(
        "CREATE TABLE IF NOT EXISTS operator_verdicts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT NOT NULL, route TEXT NOT NULL, "
        "verdict TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    q = db.query("SELECT verdict, COUNT(*) AS n FROM operator_verdicts GROUP BY verdict")
    counts = {str(r["verdict"]): int(r["n"]) for r in (q.get("rows", []) if q.get("ok") else [])}
    good = counts.get("good", 0)
    bad = counts.get("bad", 0)
    return f"رأیهای تو: {_fa(good)} 👍 / {_fa(bad)} 👎"


def _redteam_line(db: DatabaseSuite) -> str:
    from universal_mind.red_team import findings_summary

    findings = findings_summary(store=db)
    if not findings:
        return "تیم سرخ: صید صفر — همهی پاسخهای خصمانه صادق ماندند"
    return f"تیم سرخ: {_fa(len(findings))} یافتهی باز (هدفِ ترمیم ثبت شده)"


def self_status(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """The five-signal health answer — each signal honest on its own."""
    store = db or DatabaseSuite.shared_persistent()
    lines: list[str] = []
    signals: dict[str, str] = {}
    readers: list[tuple[str, Callable[[], str]]] = [
        ("pulse", lambda: _pulse_line(store)),
        ("drift", _drift_line),
        ("backup", _backup_line),
        ("verdicts", lambda: _verdict_line(store)),
        ("red_team", lambda: _redteam_line(store)),
    ]
    for name, reader in readers:
        try:
            signals[name] = reader()
        except Exception as exc:  # noqa: BLE001 — a dead gauge says so
            signals[name] = f"— (خوانده نشد: {exc})"
        lines.append(f"• {signals[name]}")
    report = "وضعیت خودم، از پنج سیگنالِ زنده:\n" + "\n".join(lines)
    return {"ok": True, "signals": signals, "report": report, "error": ""}
