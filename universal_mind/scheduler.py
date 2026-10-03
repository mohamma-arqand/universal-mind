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
    """One persisted task — repeating, or a one-shot reminder (R53 wave-2)."""

    schedule_id: int
    command: str          # the Persian command to run when due
    every_minutes: int     # the interval (1440 = daily at the fixed hour)
    hour_of_day: int       # for daily schedules: the fixed hour (else -1)
    minute_of_hour: int = 0  # R45-2: the minute within the hour (else 0)
    last_run: str = ""    # ISO timestamp of the last real firing ('' = never)
    active: bool = True
    kind: str = ""        # '' = repeating; 'once' = one-shot reminder (R53)
    run_at: str = ""      # for kind='once': the LOCAL ISO moment to fire


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
    # R45-2 — halves and quarters FIRST (the fuller form wins):
    # «ساعت ۸ و نیم» / «ساعت ۷ و ربع» / «ساعت ۸:30».
    daily_hm = re.search(r"هر روز ساعت (\d{1,2})(?::(\d{1,2})| و (نیم|ربع))", text)
    if daily_hm:
        hour = int(daily_hm.group(1))
        if not 0 <= hour <= 23:
            return None
        if daily_hm.group(2):  # the 08:30 form
            minute = int(daily_hm.group(2))
        else:  # the «و نیم/و ربع» form
            minute = 30 if daily_hm.group(3) == "نیم" else 15
        if 0 <= minute <= 59:
            return {"every_minutes": 1440, "hour_of_day": hour, "minute_of_hour": minute}
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


# R53 wave-2 — ONE-SHOT TIME WORDS (the local clock, the operator's words).
_FA_NUMS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _re_search_her(text: str) -> bool:
    """True when the sentence carries the REPEATING marker «هر ...».

    «هر روز» / «هر ۳۰ دقیقه» / «هر وقت» — an interval, not a moment. Written
    as its own helper because the word «هر» also appears inside other words;
    the check is on the standalone token preceding a time word.
    """
    import re

    return bool(re.search(r"\bهر\b", text) or re.search(r"هر (روز|دقیقه|ساعت|هفته|ماه|وقت)", text))


def parse_one_shot(command: str, now: datetime | None = None) -> dict[str, Any] | None:
    """Extract a ONE-SHOT moment from Persian, or None.

    Honest forms (LOCAL clock — the one-clock law):
      «فردا ساعت ۸ ...» / «فردا صبح ساعت ۷:30 ...»  → tomorrow at H[:M]
      «امشب ساعت ۲۱ ...» / «امشب ۹ ...»              → today at H (evening)
      «ساعت ۱۵:۳۰ ...» / «ساعت ۳ و نیم ...»          → today (or tomorrow if past)
      «پس‌فردا ساعت ۸ ...»                             → day after tomorrow
    «صبح/صبح زود» alone → tomorrow 08:00; «ظهر» → today 12:00 (or tomorrow).
    None = no one-shot moment in the sentence (repeating/other syntax).
    """
    import re

    text = command.translate(_FA_NUMS)
    text = text.replace("\u200c", " ")  # ZWNJ → space for پس‌فردا
    current = now or datetime.now()
    # REPEATING IS NOT ONE-SHOT: «هر روز ساعت ۸» / «هر ۳۰ دقیقه» carry an
    # interval (هر) — they belong to parse_schedule, never to a single moment.
    if _re_search_her(text):
        return None

    def _at(day_offset: int, hour: int, minute: int) -> datetime:
        candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        candidate = candidate + timedelta(days=day_offset)
        if day_offset == 0 and candidate <= current:
            candidate += timedelta(days=1)  # «ساعت ۸» at 9am means TOMORROW 8
        return candidate

    # explicit hour first — it names the moment precisely
    hm = re.search(r"ساعت (\d{1,2})(?::(\d{1,2})| و (نیم|ربع))?", text)
    day = 0
    if "پس فردا" in text or "پس‌فردا" in command:
        day = 2
    elif "فردا" in text:
        day = 1
    elif "امشب" in text:
        day = 0
        if hm is None:
            hm = re.search(r"امشب (\d{1,2})(?::(\d{1,2}))?", text)
    # R62 T1 — WEEKDAY words: «جلسه شنبه ساعت ۱۰ است» names a WEEKDAY, not
    # a relative day. The distance (0..6) is real (the same longest-first
    # table the weekday-distance answer uses — شنبه is a SUBSTRING of
    # یکشنبه/دوشنبه/…; the longer words are tested first). 0 = today.
    # THE DISTANCE IS COMPUTED, NEVER TABLE-READ: the table maps a weekday
    # WORD to Python's weekday() NUMBER (Monday=0…Sunday=6) — the live
    # witness caught the first draft reading the table VALUE as an offset
    # (شنبه fired on چهارشنبه while Saturday was TOMORROW). The real
    # distance is (target - today) % 7; «آینده» forces the NEXT cycle.
    _WD = None
    # NOTE: the ZWNJ was normalized to a SPACE above («سه‌شنبه» arrives as
    # «سه شنبه») — the table must carry BOTH spellings or the real spoken
    # form falls through to a wrong day (a live witness caught Tuesday).
    # THE SUBSTRING LAW, FOURTH BITE: «جلسه شنبه» CONTAINS «سه شنبه»
    # (the س+ه of جلسه + space + شنبه) — a bare substring test matched
    # THREE-SHANBE inside a sentence about SHANBE. A weekday must start at
    # a WORD BOUNDARY (start-of-text or a space before it).
    for _w, _py in (("سه شنبه", 1), ("سه‌شنبه", 1), ("سهشنبه", 1), ("یکشنبه", 6),
                     ("دوشنبه", 0), ("چهار شنبه", 2), ("چهارشنبه", 2),
                     ("پنج شنبه", 3), ("پنجشنبه", 3),
                     ("شنبه", 5), ("جمعه", 4)):
        if text.startswith(_w) or (" " + _w) in text:
            _dist = (_py - datetime.now().weekday()) % 7
            if _dist == 0 and "آینده" in text:
                _dist = 7  # «شنبهٔ آینده» on a Saturday = NEXT Saturday
            _WD = _dist
            break

    if hm:
        hour = int(hm.group(1))
        minute = 0
        if hm.group(2):
            minute = int(hm.group(2))
        elif hm.group(3) == "نیم":
            minute = 30
        elif hm.group(3) == "ربع":
            minute = 15
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            if _WD is not None:
                day = _WD
            return {"run_at": _at(day, hour, minute).isoformat(), "day_offset": day}
        if _WD is not None and (hour > 23 or minute > 59):
            return {"run_at": _at(_WD, 8, 0).isoformat(), "day_offset": _WD}

    # bare day-words: صبح زود/فردا صبح → 08:00, ظهر → 12:00, امشب → 21:00
    if "پس فردا" in text or "پس‌فردا" in command:
        return {"run_at": _at(2, 8, 0).isoformat(), "day_offset": 2}
    if "فردا" in text:
        return {"run_at": _at(1, 8, 0).isoformat(), "day_offset": 1}
    if "صبح زود" in text:
        return {"run_at": _at(1, 6, 30).isoformat(), "day_offset": 1}
    if "امشب" in text:
        return {"run_at": _at(0, 21, 0).isoformat(), "day_offset": 0}
    if "ظهر" in text:
        return {"run_at": _at(0, 12, 0).isoformat(), "day_offset": 0}
    return None


def register_one_shot(command: str, now: datetime | None = None) -> dict[str, Any]:
    """Persist a ONE-SHOT reminder («یادم بنداز که فردا زود بیدار شوم»).

    The sentence's BODY (minus the one-shot time words) becomes the reminder
    text — what actually gets said aloud/toasted at the moment. Fires once,
    then the tick deletes it (a fired reminder that stays is a lie in the list).
    """
    moment = parse_one_shot(command, now)
    if moment is None:
        return {"ok": False, "error": "یک زمانِ یکبارمصرف در جمله پیدا نکردم", "id": None}
    body = command.strip()
    for noise in ("یادم بنداز که", "یادم بنداز", "یادآوری کن که", "یادآوری کن",
                  "یادم باشه که", "یادم باشه", "یادم باشی که", "یادم باشی",
                  "یادم بشه", "یادم بشی", "یادم بادی", "یادم باش",
                  "یادت باشه", "یادت نره", "به یادم بیار که", "به یادم بیار",
                  "یادت باشد", "— یادت باشد", "- یادت باشد"):
        if body.startswith(noise):
            body = body[len(noise):].strip()
            break
    body = body or command.strip()
    # R62 T1 — a TRAILING marker is not part of the appointment text either:
    # «جلسه شنبه ساعت ۱۰ است — یادت باشد» must SAY the meeting, not the
    # marker. Strip trailing remember-markers (and the dash noise before them).
    for trailer in ("— یادت باشد", "- یادت باشد", "یادت باشد",
                    "— یادم باشه", "- یادم باشه", "یادم باشه"):
        if body.endswith(trailer):
            body = body[: -len(trailer)].strip(" :،.-—")
            break
    db = _store()
    _ensure_table(db)
    db.insert_many("schedules", [{
        "command": body,
        "every_minutes": "0",
        "hour_of_day": "-1",
        "minute_of_hour": "0",
        "last_run": "",
        "active": "1",
        "kind": "once",
        "run_at": moment["run_at"],
    }])
    # WHEN (in Persian): فردا/امشب + ساعت — the operator reads time in words.
    fire = datetime.fromisoformat(moment["run_at"])
    days_fa = {0: "امروز", 1: "فردا", 2: "پس‌فردا"}.get(moment["day_offset"], "")
    h = _fa_num(fire.hour)
    m = _fa_num(fire.minute)
    clock = f"ساعت {h}" + (f":{m}" if fire.minute else "")
    when_fa = f"{days_fa} {clock}".strip()
    return {"ok": True, "id": None, "run_at": moment["run_at"], "when_fa": when_fa,
            "reminder": body, "error": ""}


def toggle_schedule(schedule_id: int, active: bool) -> dict[str, Any]:
    """Arm/disarm a schedule BY ID — the row SURVIVES (a paused reminder is
    not a deleted one; the operator's history stays theirs)."""
    db = _store()
    _ensure_table(db)
    try:
        db.execute(
            f"UPDATE schedules SET active = {1 if active else 0} "
            f"WHERE id = {int(schedule_id)}")
    except Exception as exc:  # noqa: BLE001 — the toggle reports, never crashes
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "id": int(schedule_id), "active": active, "error": ""}


def delete_schedule(schedule_id: int) -> dict[str, Any]:
    """Remove a schedule/reminder BY ID (the operator's explicit intent)."""
    db = _store()
    _ensure_table(db)
    try:
        db.execute(f"DELETE FROM schedules WHERE id = {int(schedule_id)}")
    except Exception as exc:  # noqa: BLE001 — deletion reports, never crashes
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "deleted": int(schedule_id), "error": ""}


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
        r"هر روز ساعت \d{1,2}(?::\d{1,2}| و (?:نیم|ربع))? ?"
        r"|هر \d+ دقیقه ?|هر \d+ ساعت ?", re.IGNORECASE
    )
    out = command
    while (m := pattern.search(_normalize_fa_numbers(out))):
        out = out[: m.start()] + out[m.end():]
    # R65 P2 — «یکبار» after an interval is the REPEATING filler, not the
    # action's first word («هر ۳۰ دقیقه یکبار بهم بگو آب بخورم» stored
    # «یکبار بهم بگو …»).
    out = re.sub(r"^یک\s*بار\s+", "", out.strip())
    return out.strip()


def _store() -> DatabaseSuite:
    # R41: shared — patches reach it; one hot wrapper.
    return DatabaseSuite.shared_persistent()


def _ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("schedules", [
        "CREATE TABLE IF NOT EXISTS schedules ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT, every_minutes INTEGER, hour_of_day INTEGER, "
        "last_run TEXT DEFAULT '', active INTEGER DEFAULT 1)",
    ])
    try:
        cols = db.query("SELECT name FROM pragma_table_info('schedules')")
        names = {str(r["name"]) for r in cols.get("rows", [])} if cols.get("ok") else set()
        if "minute_of_hour" not in names:
            db.execute("ALTER TABLE schedules ADD COLUMN minute_of_hour INTEGER DEFAULT 0")
        # R53 wave-2 — THE ONE-SHOT REMINDER: a reminder with an explicit
        # run_at fires ONCE (kind='once') and is deleted after firing; kind=''
        # (or NULL) keeps every pre-existing row a REPEATING schedule. The
        # same table, the same tick, zero migration for existing rows.
        if "kind" not in names:
            db.execute("ALTER TABLE schedules ADD COLUMN kind TEXT DEFAULT ''")
        if "run_at" not in names:
            db.execute("ALTER TABLE schedules ADD COLUMN run_at TEXT DEFAULT ''")
    except Exception:  # noqa: BLE001 — migration is best-effort, never fatal
        pass


def register(command: str) -> dict[str, Any]:
    """Persist a scheduled task OR a folder watcher from a Persian sentence.

    A sentence that carries BOTH a goal («هدف: ...») and a schedule clause
    («هر روز ساعت ۸») becomes a SCHEDULED GOAL: at each firing, the agent
    loop pursues the goal's steps fresh (the operator's objectives become
    part of the proactive routine).
    """
    watcher = parse_folder_watcher(command)
    if watcher is not None:
        return _register_watcher(watcher["folder"], watcher["action"])
    if "هدف" in command:
        spec = parse_schedule(command)
        if spec is not None:
            from universal_mind.goal_parser import parse_goal

            goal = parse_goal(command)
            if goal is not None and goal.steps:
                db = _store()
                _ensure_table(db)
                action = " | ".join(goal.steps)
                db.insert_many(
                    "schedules",
                    [{
                        "command": f"__goal__{action}",
                        "every_minutes": str(spec["every_minutes"]),
                        "hour_of_day": str(spec["hour_of_day"]),
                        "minute_of_hour": str(spec.get("minute_of_hour", 0)),
                        "last_run": "", "active": "1",
                    }],
                )
                return {"ok": True, "scheduled_goal": True,
                        "steps": list(goal.steps),
                        "every_minutes": spec["every_minutes"],
                        "hour_of_day": spec["hour_of_day"],
                        "minute_of_hour": int(spec.get("minute_of_hour", 0)),
                        "error": ""}
        return {"ok": False, "error": "هدفِ زمانبندیشده بند زمان ندارد — «هر روز ساعت ۸» یا «هر ۳۰ دقیقه» اضافه کن"}
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
            "minute_of_hour": str(spec.get("minute_of_hour", 0)),
            "last_run": "",
            "active": "1",
        }],
    )
    return {
        "ok": True,
        "command": action,
        "every_minutes": spec["every_minutes"],
        "hour_of_day": spec["hour_of_day"],
        "minute_of_hour": int(spec.get("minute_of_hour", 0)),
        "error": "",
    }


def list_schedules() -> list[Schedule]:
    """Every persisted schedule (the operator's real task table)."""
    db = _store()
    _ensure_table(db)
    q = db.query(
        "SELECT id, command, every_minutes, hour_of_day, minute_of_hour, "
        "last_run, active, kind, run_at FROM schedules ORDER BY id"
    )
    if not q.get("ok"):
        return []
    out: list[Schedule] = []
    for r in q["rows"]:
        out.append(Schedule(
            schedule_id=int(r["id"]),
            command=str(r["command"]),
            every_minutes=int(r["every_minutes"]),
            hour_of_day=int(r["hour_of_day"]),
            minute_of_hour=int(r["minute_of_hour"] or 0),
            last_run=str(r["last_run"] or ""),
            active=bool(int(r["active"])),
            kind=str(r.get("kind") or ""),
            run_at=str(r.get("run_at") or ""),
        ))
    return out


def _next_due(schedule: Schedule, now: datetime | None = None) -> datetime | None:
    """When this schedule is next due (None = never)."""
    current = now or datetime.now()
    if not schedule.active:
        return None
    # R53 wave-2 — a one-shot reminder is due exactly at its run_at (LOCAL,
    # the operator's clock — the one-clock law), never before, never after.
    if schedule.kind == "once":
        if not schedule.run_at:
            return None  # an armless one-shot is honestly never due
        try:
            return datetime.fromisoformat(schedule.run_at)
        except ValueError:
            return None  # a malformed run_at never fires blindly
    if not schedule.last_run:
        return current  # never ran → due immediately
    try:
        last = datetime.fromisoformat(schedule.last_run)
    except ValueError:
        return current
    if schedule.hour_of_day >= 0:
        # Daily at a fixed hour: due at today's (or tomorrow's) H:00.
        candidate = current.replace(
            hour=schedule.hour_of_day,
            minute=schedule.minute_of_hour, second=0, microsecond=0,
        )
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


def _contest_for(command: str, primary: dict[str, Any]) -> str:
    """Race the primary run against its honest rival; return the outcome.

    The contest is read-only for the operator (the primary result already
    shipped); its value is the LESSON — which order won, recorded so the
    advisor's next advice is sharper. Single-capability routes report
    'no contest' honestly.
    """
    try:
        from universal_mind.contested_execution import run_contested
        from universal_mind.persian_router import route_and_run as _run

        route = tuple(primary.get("route", []))
        if len(route) < 2:
            return "بدون مسابقه — مسیر تک‌مرحله‌ای بود"

        def _run_candidate(candidate: tuple[str, ...]) -> dict[str, Any]:
            return _run(command, forced_route=list(candidate))

        verdict = run_contested(command, route, _run_candidate)
        if not verdict.contested:
            return "بدون مسابقه — رقیب صادقانه‌ای نبود"
        winner = verdict.winner.route if verdict.winner else route
        if winner == route:
            return f"مسابقه: مسیر توصیه‌شده برنده شد ({verdict.reasoning[:60]})"
        return f"مسابقه: رقیب برنده شد — درس ثبت شد ({verdict.reasoning[:60]})"
    except Exception as exc:  # noqa: BLE001 — the contest is a lens, never a blocker
        return f"مسابقه ناموفق: {str(exc)[:60]}"


def mark_run(schedule_id: int, when: datetime | None = None) -> None:
    """Record a REAL firing (the schedule's honest last_run)."""
    db = _store()
    _ensure_table(db)
    stamp = (when or datetime.now()).isoformat()
    db.execute(f"UPDATE schedules SET last_run = '{stamp}' WHERE id = {schedule_id}")


def run_due(max_runs: int = 5, *, contest: bool = True) -> dict[str, Any]:
    """Fire every due schedule through the REAL engine; return what ran.

    With ``contest=True`` (the default) every multi-step scheduled run also
    races its honest rival order — ARETĒ judges both, the best verdict ships,
    and the contest outcome is recorded: while the operator is away the
    platform not only runs, it EXPLORES, and the winning order sharpens the
    advisor's next advice.
    """
    from universal_mind.persian_router import route_and_run

    fired: list[dict[str, Any]] = []
    # R46-13 — A BROKEN STORE NEVER KILLS THE TICK: reading the schedules
    # through a locked/corrupt store is an HONEST failure with a name (it
    # lands in tick_health and reaches a toast), never an uncaught crash.
    try:
        due_now = due_schedules()
    except Exception as exc:  # noqa: BLE001 — the failure IS the report
        return {
            "fired": [], "count": 0, "error": f"خواندنِ زمانبندیها ناموفق: {exc}",
            "ok": False,
        }
    # POISON-DOWN: goals that halted 3+ times at the same step are NOT
    # re-spawned by the tick — the self-inspection reports them instead.
    try:
        from universal_mind.agent_loop import _poisoned_goals

        poison_names: set[str] = set()
        db = _store()
        _ensure_table(db)
        for gid in _poisoned_goals():
            gq = db.query("SELECT goal FROM goals WHERE id = ?", (str(gid),))
            if gq.get("ok") and gq["rows"]:
                poison_names.add(str(gq["rows"][0]["goal"]))
    except Exception:  # noqa: BLE001
        poison_names = set()

    for schedule in due_now[:max_runs]:
        if schedule.command.removeprefix("__goal__") in poison_names or schedule.command in poison_names:
            mark_run(schedule.schedule_id)  # the clock advances; the poison stays visible
            continue
        try:
            if schedule.command.startswith("__goal__"):
                # A SCHEDULED GOAL: the agent pursues the steps afresh.
                from universal_mind.agent_loop import goal_run_report, run_goal, start_goal

                steps = tuple(schedule.command.removeprefix("__goal__").split(" | "))
                started = start_goal(f"زمانبندی: {' و '.join(steps)}", steps)
                goal_result = run_goal(started["goal_id"])
                entry: dict[str, Any] = {
                    "schedule_id": schedule.schedule_id,
                    "command": schedule.command.removeprefix("__goal__"),
                    "ok": goal_result.finished,
                    "route": ["goal"],
                }
                # The goal's OUTCOME, said ALOUD (the tick already toasts; the
                # voice closes the perception loop for the operator's ears).
                try:
                    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
                    n_steps = str(len(goal_result.steps)).translate(fa)
                    spoken = (
                        f"هدف زمانبندیشده تمام شد؛ {n_steps} گام اجرا شد."
                        if goal_result.finished
                        else f"هدف زمانبندیشده در گامی متوقف شد؛ {goal_result.reasoning[:80]}"
                    )
                    from universal_mind.speech_tool import SpeechTool

                    SpeechTool().speak(spoken)
                except Exception:  # noqa: BLE001 — the voice is a bonus, never fatal
                    pass
                if len(goal_result.steps) >= 2:
                    entry["contest"] = goal_run_report(goal_result).replace("\n", " ")[:100]
                mark_run(schedule.schedule_id)
                fired.append(entry)
                continue
            if schedule.kind == "once":
                # R53 wave-2 — A ONE-SHOT REMINDER: the body IS the message.
                # Toast it, say it (the mute law applies), then DELETE the row:
                # a fired reminder that stays in the list is a lie.
                from universal_mind.real_notify import NotifyTool
                from universal_mind.speech_tool import SpeechTool

                NotifyTool().notify("یادآور", schedule.command)
                try:
                    SpeechTool().speak(schedule.command)
                except Exception:  # noqa: BLE001 — the voice is a bonus
                    pass
                delete_schedule(schedule.schedule_id)
                fired.append({
                    "schedule_id": schedule.schedule_id,
                    "command": schedule.command,
                    "ok": True, "route": ["reminder"], "once": True,
                })
                continue
            payload: dict[str, Any] = route_and_run(schedule.command)
            cmd_entry: dict[str, Any] = {
                "schedule_id": schedule.schedule_id,
                "command": schedule.command,
                "ok": payload.get("ok") is True,
                "route": payload.get("route", []),
            }
            if contest and len(str(cmd_entry.get("route", []))) >= 2:
                cmd_entry["contest"] = _contest_for(schedule.command, payload)
            mark_run(schedule.schedule_id)
            fired.append(cmd_entry)
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


def backup_database(keep: int = 3) -> dict[str, Any]:
    """A rotating safe copy of the persistent store (the corruption lesson).

    Copies mind.db to mind.db.bak-<timestamp> and prunes to the newest
    ``keep`` copies. An honest failure (db busy, disk full) reports why —
    never a silent skip: the backup IS the recovery path, its health matters.
    """
    from datetime import datetime as _dt

    src = DatabaseSuite.DEFAULT_DB_DIR / "mind.db"
    if not src.exists():
        return {"ok": False, "error": "mind.db does not exist", "backups": []}

    def _prune() -> list[str]:
        """Keep only the newest `keep` timestamped backups.

        Runs BEFORE the new copy and on every failure path: a failed backup
        (a full disk was the live case) used to return early and leave its
        junk file behind, so the directory grew without bound exactly when
        space was scarcest.
        """
        pruned: list[str] = []
        existing = sorted(
            (f for f in src.parent.glob("mind.db.bak-2*") if f.is_file()),
            key=lambda f: f.name,
        )
        for old_file in existing[:-keep] if len(existing) > keep else []:
            try:
                old_file.unlink()
                pruned.append(old_file.name)
            except OSError:
                pass
        return pruned

    _prune()
    stamp = _dt.now().strftime("%Y%m%d-%H%M%S")
    dst = src.parent / f"mind.db.bak-{stamp}"
    try:
        # SQLite's own backup API — consistent even under concurrent writes
        # (a raw file copy can catch a half-written page: the corruption lesson).
        import sqlite3

        # Explicit close — `with sqlite3.connect(...)` COMMITS but NEVER
        # CLOSES (the fd-leak class): the open handle then locks dst, so the
        # cleanup unlink below fails with WinError 32 and the junk file stays
        # behind exactly when space was scarcest (this function's own law).
        source = sqlite3.connect(str(src))
        target = sqlite3.connect(str(dst))
        try:
            source.backup(target)
        finally:
            source.close()
            target.close()
    except (OSError, sqlite3.Error) as exc:
        try:
            dst.unlink()
        except OSError:
            pass
        return {"ok": False, "error": str(exc), "backups": []}
    # VERIFY: a backup that cannot be read is not a backup.
    try:
        probe = sqlite3.connect(str(dst))
        check = probe.execute("PRAGMA integrity_check").fetchone()[0]
        probe.close()
    except sqlite3.Error as exc:
        try:
            dst.unlink()
        except OSError:
            pass
        return {"ok": False, "error": f"backup verify failed: {exc}", "backups": []}
    if check != "ok":
        try:
            dst.unlink()
        except OSError:
            pass
        return {"ok": False, "error": f"backup corrupt: {check}", "backups": []}
    pruned = _prune()
    remaining = len(list(src.parent.glob("mind.db.bak-2*")))
    return {"ok": True, "backup": str(dst), "bytes": dst.stat().st_size,
            "total_backups": remaining, "pruned": len(pruned), "error": ""}


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