"""Scheduled tasks — the platform runs itself on the operator's clock.

The Persian layer speaks time too: «هر روز ساعت ۸ گزارش کامل بده» registers a
recurring task, and a runner executes whatever is DUE — the platform becomes
proactive instead of purely reactive.

Honest rules:
- A schedule is a REAL persisted record (the table, the interval, the command,
  the last run) — never an in-memory promise that dies with the process.
- The runner only fires what is DUE; nothing fabricates a run.
- Executions go through the SAME route_and_run engine (schedules are just
  commands with a clock attached), and every fired run lands in history
  exactly like a manual one.
- Parsing is explicit: «هر N دقیقه/ساعت» and «هر روز ساعت H» are the two
  honest forms; anything else fails with the exact syntax, never a guess.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


@dataclass(frozen=True)
class Schedule:
    """One persisted recurring task."""

    schedule_id: int
    command: str          # the Persian command to run when due
    every_minutes: int     # the interval (1440 = daily at the fixed hour)
    hour_of_day: int       # for daily schedules: the fixed hour (else -1)
    last_run: str          # ISO timestamp of the last real firing ('' = never)
    active: bool


def _normalize_fa_numbers(text: str) -> str:
    return text.translate(_FA_DIGITS)


def parse_schedule(command: str) -> dict[str, Any] | None:
    """Extract a schedule spec from a Persian sentence, or None.

    Honest forms:
      «هر N دقیقه ...»  → every N minutes
      «هر N ساعت ...»    → every N*60 minutes
      «هر روز ساعت H ...» → daily at H:00 (every_minutes=1440, hour=H)
    Anything else → None (the caller reports the syntax honestly).

    Folder watchers («هر وقت در پوشهی X ...») are NOT time schedules —
    parse_folder_watcher handles them separately.
    """
    if "هر وقت" in command and "پوشه" in command:
        return None  # a folder watcher, not a time schedule
    text = _normalize_fa_numbers(command)
    daily = re.search(r"هر روز ساعت (\d{1,2})", text)
    if daily:
        hour = int(daily.group(1))
        if 0 <= hour <= 23:
            return {"every_minutes": 1440, "hour_of_day": hour}
    minutes = re.search(r"هر (\d+) دقیقه", text)
    if minutes:
        n = int(minutes.group(1))
        if n > 0:
            return {"every_minutes": n, "hour_of_day": -1}
    hours = re.search(r"هر (\d+) ساعت", text)
    if hours:
        n = int(hours.group(1))
        if n > 0:
            return {"every_minutes": n * 60, "hour_of_day": -1}
    return None


def parse_folder_watcher(command: str) -> dict[str, Any] | None:
    """Extract a folder-watcher spec from a Persian sentence, or None.

    Honest form: «هر وقت در پوشهی X فایل جدید آمد، Y» — X is resolved
    through the Persian layer's real folder resolution (دسکتاپ، دانلودز،
    or an absolute path), and Y is the action to run on each new file.
    The action may reference the file with «فایلش» (the flow layer substitutes
    the real path). Anything else → None.
    """
    if "هر وقت" not in command or "پوشه" not in command:
        return None
    m = re.search(r"(?:در پوشهی|در پوشهی|پوشهی|پوشه) (.+?) فایل جدید", command)
    if not m:
        return None
    folder_hint = m.group(1).strip()
    action = re.sub(r"هر وقت .*? فایل جدید (?:امد|آمد|اومد)،? ?", "", command).strip()
    if not action:
        return None
    # Resolve the real folder through the existing Persian layer.
    from universal_mind.persian_params import resolve_folder

    folder = resolve_folder(command) or _resolve_known_folder(folder_hint)
    if not folder or not os.path.isdir(folder):
        return None
    return {"folder": folder, "action": action, "error": ""}


def _resolve_known_folder(hint: str) -> str:
    """The standard Windows folders by Persian name (Downloads, Desktop...)."""
    home = os.path.expanduser("~")
    mapping = {
        "دانلود": os.path.join(home, "Downloads"),
        "دانلودز": os.path.join(home, "Downloads"),
        "دسکتاپ": os.path.join(home, "Desktop"),
        "میز کار": os.path.join(home, "Desktop"),
        "اسناد": os.path.join(home, "Documents"),
        "تصاویر": os.path.join(home, "Pictures"),
    }
    for key, path in mapping.items():
        if key in hint and os.path.isdir(path):
            return path
    # an absolute path given directly
    if os.path.isdir(hint):
        return hint
    return ""


def _strip_schedule_words(command: str) -> str:
    """The actionable command underneath the schedule clause.

    The schedule words are located on the NORMALIZED text (Persian digits
    parse as numbers) but removed from the ORIGINAL — the action keeps its
    Persian digits exactly as the operator wrote them.
    """
    pattern = re.compile(
        r"هر روز ساعت \d{1,2} ?|هر \d+ دقیقه ?|هر \d+ ساعت ?", re.IGNORECASE
    )
    out = command
    while (m := pattern.search(_normalize_fa_numbers(out))):
        out = out[: m.start()] + out[m.end():]
    return out.strip()


def _store() -> DatabaseSuite:
    return DatabaseSuite(persistent=True)


def _ensure_table(db: DatabaseSuite) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS schedules ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT, every_minutes INTEGER, hour_of_day INTEGER, "
        "last_run TEXT DEFAULT '', active INTEGER DEFAULT 1)"
    )


def register(command: str) -> dict[str, Any]:
    """Persist a scheduled task OR a folder watcher from a Persian sentence."""
    watcher = parse_folder_watcher(command)
    if watcher is not None:
        return _register_watcher(watcher["folder"], watcher["action"])
    spec = parse_schedule(command)
    if spec is None:
        return {
            "ok": False, "error": (
                "زمانبندی نفهمیدم — قالب درست: «هر ۳۰ دقیقه ...» یا «هر روز ساعت ۸ ...» "
                "یا «هر وقت در پوشهی دانلود فایل جدید آمد، ...»"
            ),
        }
    action = _strip_schedule_words(command)
    if not action:
        return {"ok": False, "error": "فرمانی برای زمانبندی نبود"}
    db = _store()
    _ensure_table(db)
    db.insert_many(
        "schedules",
        [{
            "command": action,
            "every_minutes": str(spec["every_minutes"]),
            "hour_of_day": str(spec["hour_of_day"]),
            "last_run": "",
            "active": "1",
        }],
    )
    return {
        "ok": True,
        "command": action,
        "every_minutes": spec["every_minutes"],
        "hour_of_day": spec["hour_of_day"],
        "error": "",
    }


def list_schedules() -> list[Schedule]:
    """Every persisted schedule (the operator's real task table)."""
    db = _store()
    _ensure_table(db)
    q = db.query("SELECT id, command, every_minutes, hour_of_day, last_run, active FROM schedules ORDER BY id")
    if not q.get("ok"):
        return []
    out: list[Schedule] = []
    for r in q["rows"]:
        out.append(Schedule(
            schedule_id=int(r["id"]),
            command=str(r["command"]),
            every_minutes=int(r["every_minutes"]),
            hour_of_day=int(r["hour_of_day"]),
            last_run=str(r["last_run"] or ""),
            active=bool(int(r["active"])),
        ))
    return out


def _next_due(schedule: Schedule, now: datetime | None = None) -> datetime | None:
    """When this schedule is next due (None = never)."""
    current = now or datetime.now()
    if not schedule.active:
        return None
    if not schedule.last_run:
        return current  # never ran → due immediately
    try:
        last = datetime.fromisoformat(schedule.last_run)
    except ValueError:
        return current
    if schedule.hour_of_day >= 0:
        # Daily at a fixed hour: due at today's (or tomorrow's) H:00.
        candidate = current.replace(hour=schedule.hour_of_day, minute=0, second=0, microsecond=0)
        if candidate <= last:
            candidate = candidate + timedelta(days=1)
        return candidate
    return last + timedelta(minutes=schedule.every_minutes)


def due_schedules(now: datetime | None = None) -> list[Schedule]:
    """The schedules whose time has come (the runner's work list)."""
    current = now or datetime.now()
    due: list[Schedule] = []
    for schedule in list_schedules():
        nxt = _next_due(schedule, current)
        if nxt is not None and nxt <= current:
            due.append(schedule)
    return due


def mark_run(schedule_id: int, when: datetime | None = None) -> None:
    """Record a REAL firing (the schedule's honest last_run)."""
    db = _store()
    _ensure_table(db)
    stamp = (when or datetime.now()).isoformat()
    db.execute(f"UPDATE schedules SET last_run = '{stamp}' WHERE id = {schedule_id}")


def run_due(max_runs: int = 5) -> dict[str, Any]:
    """Fire every due schedule through the REAL engine; return what ran."""
    from universal_mind.persian_router import route_and_run

    fired: list[dict[str, Any]] = []
    for schedule in due_schedules()[:max_runs]:
        try:
            payload = route_and_run(schedule.command)
            mark_run(schedule.schedule_id)
            fired.append({
                "schedule_id": schedule.schedule_id,
                "command": schedule.command,
                "ok": payload.get("ok") is True,
                "route": payload.get("route", []),
            })
        except Exception as exc:  # noqa: BLE001 — one bad task never stops the rest
            fired.append({
                "schedule_id": schedule.schedule_id,
                "command": schedule.command,
                "ok": False,
                "error": str(exc),
            })
            mark_run(schedule.schedule_id)  # even failures advance the clock

    # The proactive loop is VISIBLE: when the tick did autonomous work, a real
    # Windows toast says what ran (a tick that fired nothing stays silent —
    # silence is the honest state for 'nothing was due').
    if fired:
        ok_count = sum(1 for f in fired if f.get("ok"))
        body = (
            f"{_fa_num(len(fired))} کارِ زمان‌بندی‌شده اجرا شد"
            + (f" ({_fa_num(ok_count)} موفق)" if ok_count != len(fired) else "")
        )
        try:
            from universal_mind.real_notify import NotifyTool

            NotifyTool().notify(title="ذهن یکپارچه — اجرای خودکار", body=body)
        except Exception:  # noqa: BLE001 — the toast is a bonus, never fatal
            pass

    return {"ok": True, "fired": fired, "count": len(fired), "error": ""}


def _fa_num(value: int | float) -> str:
    """Persian digits for the toast (the operator's language everywhere)."""
    if isinstance(value, int) or (isinstance(value, float) and value == int(value)):
        text = str(int(value))
    else:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _register_watcher(folder: str, action: str) -> dict[str, Any]:
    """Persist a folder watcher (the proactive third perception channel)."""
    db = _store()
    _ensure_watcher_table(db)
    db.insert_many(
        "folder_watchers",
        [{"folder": folder, "action": action, "known_files": "", "active": "1"}],
    )
    return {"ok": True, "watcher": True, "folder": folder, "action": action, "error": ""}


def _ensure_watcher_table(db: DatabaseSuite) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS folder_watchers ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, folder TEXT, action TEXT, "
        "known_files TEXT DEFAULT '', active INTEGER DEFAULT 1)"
    )


def list_watchers() -> list[dict[str, Any]]:
    """Every persisted folder watcher."""
    db = _store()
    _ensure_watcher_table(db)
    q = db.query("SELECT id, folder, action, known_files, active FROM folder_watchers ORDER BY id")
    if not q.get("ok"):
        return []
    return [
        {
            "watcher_id": int(r["id"]), "folder": str(r["folder"]),
            "action": str(r["action"]), "known_files": str(r["known_files"] or ""),
            "active": bool(int(r["active"])),
        }
        for r in q["rows"]
    ]


def _current_files(folder: str) -> set[str]:
    """The real file names currently in the folder (honest scan)."""
    try:
        return {f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))}
    except OSError:
        return set()


def scan_watchers(max_actions: int = 5) -> dict[str, Any]:
    """Scan every active watcher's folder and run the action on NEW files.

    The FIRST scan only LEARNS the folder's contents (baseline) — firing on
    files that existed before registration would be reacting to the past,
    not to a new event. Each firing marks the file as known (once only).
    «فایلش» in the action is substituted with the real absolute path.
    """
    from universal_mind.persian_router import route_and_run

    fired: list[dict[str, Any]] = []
    db = _store()
    _ensure_watcher_table(db)
    for watcher in list_watchers():
        if not watcher["active"]:
            continue
        folder = watcher["folder"]
        current = _current_files(folder)
        known_files_raw = watcher["known_files"]
        # The baseline marker distinguishes 'learned an empty folder' from
        # 'never scanned' — otherwise an empty folder stays baseline-forever
        # and every later file looks like it existed before registration.
        if known_files_raw == "":
            _update_known(watcher["watcher_id"], current if current else {"__baseline__"})
            continue
        known = {f for f in known_files_raw.split("|") if f and f != "__baseline__"}
        known.discard("__baseline__")
        new_files = sorted(current - known)
        for name in new_files[:max_actions]:
            real_path = os.path.join(folder, name)
            action = watcher["action"].replace("فایلش", real_path)
            try:
                payload = route_and_run(action)
                fired.append({
                    "watcher_id": watcher["watcher_id"], "file": name,
                    "action": action, "ok": payload.get("ok") is True,
                })
            except Exception as exc:  # noqa: BLE001 — one file never stops the rest
                fired.append({
                    "watcher_id": watcher["watcher_id"], "file": name,
                    "action": action, "ok": False, "error": str(exc),
                })
        if new_files:
            _update_known(watcher["watcher_id"], current)
    return {"ok": True, "fired": fired, "count": len(fired), "error": ""}


def _update_known(watcher_id: int, files: set[str]) -> None:
    db = _store()
    _ensure_watcher_table(db)
    joined = "|".join(sorted(files))
    db.execute(f"UPDATE folder_watchers SET known_files = '{joined}' WHERE id = {watcher_id}")


__all__ = [
    "Schedule",
    "due_schedules",
    "list_schedules",
    "list_watchers",
    "mark_run",
    "parse_folder_watcher",
    "parse_schedule",
    "register",
    "run_due",
    "scan_watchers",
]