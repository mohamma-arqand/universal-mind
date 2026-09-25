"""The reflexive class — questions the platform answers about ITSELF.

«چند تا اجرا موفق داشتی؟» / «موفقترین قابلیت کدومه؟» / «کدام زنجیره...» —
these are not commands to run a capability; they are questions about the
platform's own real store. The answer must be a REAL number from
run_history, never a guess, never a vague "many".

Six honest reflexes, each backed by one SQL sentence:
  - n runs / n successes / n failed
  - n goals by state
  - the most successful chain (with its real win count)
  - the most successful capability (aggregate over chains)
  - the last thing made (the newest successful run's command)
  - the help line (the capability list, counted for real)
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa_num(value: int | float | str) -> str:
    return str(value).translate(_FA)


def _query(db: DatabaseSuite, sql: str) -> list[dict[str, Any]]:
    try:
        q = db.query(sql)
        return q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — a reflex never crashes the router
        return []


def answer_reflexive(command: str) -> dict[str, Any] | None:
    """Route a self-question to its real answer — or None (not reflexive).

    None means the command is NOT a question about the platform; the
    ordinary router continues. A matched reflex NEVER runs a capability —
    it reads the store and answers.
    """
    db = _store()
    c = command.strip()

    # «چند تا اجرا موفق داشتی؟» — the run counts, real.
    if "چند تا" in c or "چندتا" in c:
        if "هدف" in c:
            rows = _query(db, "SELECT state, COUNT(*) AS n FROM goals WHERE state != 'archived' GROUP BY state")
            if not rows:
                return _reflex_answer(c, "هنوز هدفی ثبت نشده.")
            parts = [f"{state_fa(r['state'])}: {_fa_num(r['n'])}" for r in rows]
            return _reflex_answer(c, "هدفها — " + "، ".join(parts))
        total = _query(db, "SELECT COUNT(*) AS n FROM run_history")
        ok_n = _query(db, "SELECT COUNT(*) AS n FROM run_history WHERE succeeded = 1")
        n = int(total[0]["n"]) if total else 0
        okc = int(ok_n[0]["n"]) if ok_n else 0
        return _reflex_answer(
            c,
            f"{_fa_num(n)} اجرا ثبت شده؛ {_fa_num(okc)} موفق ({_fa_num(round(100 * okc / n) if n else 0)}٪).",
        )

    # «موفقترین زنجیره/قابلیت کدومه؟» — the real ranking.
    if "کدام" in c or "کدوم" in c or "موفقترین" in c:
        rows = _query(
            db,
            "SELECT route, COUNT(*) AS n FROM run_history "
            "WHERE succeeded = 1 AND route != '' GROUP BY route ORDER BY n DESC LIMIT 1",
        )
        if not rows:
            return _reflex_answer(c, "هنوز اجرای موفقی ثبت نشده.")
        if "قابلیت" in c:
            cap_rows = _query(
                db,
                "SELECT route FROM run_history WHERE succeeded = 1 AND route != ''",
            )
            counts: dict[str, int] = {}
            for r in cap_rows:
                for cap in str(r["route"]).split(","):
                    cap = cap.strip()
                    if cap:
                        counts[cap] = counts.get(cap, 0) + 1
            if not counts:
                return _reflex_answer(c, "هنوز قابلیتی اجرا نشده.")
            best = max(counts, key=lambda k: counts[k])
            return _reflex_answer(c, f"موفقترین قابلیت: {best} ({_fa_num(counts[best])} اجرا).")
        return _reflex_answer(
            c,
            f"موفقترین زنجیره: {rows[0]['route']} با {_fa_num(rows[0]['n'])} برد.",
        )

    # «ترندها رو نشون بده» — the session's REAL trend, not a guess: the
    # daily excellence verdict already computed by history_analytics.
    if "ترند" in c or "روند" in c:
        try:
            from universal_mind.history_analytics import session_verdict

            sv = session_verdict()
            if sv.get("ok"):
                mean_raw = sv.get("mean_excellence", sv.get("mean", 0))
                mean_pct = _fa_num(round(float(mean_raw) * 100))
                runs_n = _fa_num(sv.get("runs", 0))
                return _reflex_answer(
                    c,
                    f"روند داوری نشست: {sv['verdict']} — میانگین {mean_pct}٪ روی {runs_n} اجرا.",
                )
        except Exception:  # noqa: BLE001 — a reflex never crashes
            pass
        return _reflex_answer(c, "هنوز دادهی روندی ندارم — چند فرمان بده تا روند شکل بگیرد.")

    # «آخرین چیزی که ساختی؟» / «چیزی که قبلا ساختی رو نشونم بده» — the
    # newest real success, in ANY spoken shape (قبلا/این چند روز).
    # («دیروز» alone is a TIME WINDOW (R45-1) unless it asks to SHOW something.)
    if (
        ("آخرین" in c or "قبلا" in c or ("دیروز" in c and ("نشون" in c or "نشان" in c)))
        and ("ساختی" in c or "کردی" in c or "ساخت" in c)
    ):
        rows = _query(
            db,
            "SELECT command, route FROM run_history WHERE succeeded = 1 AND route != '' ORDER BY id DESC LIMIT 1",
        )
        if not rows:
            return _reflex_answer(c, "هنوز چیزی نساختهایم.")
        return _reflex_answer(c, f"آخرین کار موفق: «{rows[0]['command']}» ({rows[0]['route']}).")

    # «راهنما / چیکار میتونی بکنی؟ / چی بلدی؟ / قابلیتهات» — the list, counted.
    if (
        c in ("راهنما", "help")
        or "چیکار میتونی" in c
        or "چی کار میتونی" in c
        or "چی بلدی" in c
        or "چه بلدی" in c
        or "قابلیتهات" in c
        or "قابلیت هات" in c
        or ("قابلیت" in c and ("نشون" in c or "بگو" in c or "لیست" in c or "فهرست" in c))
    ):
        from universal_mind.real_tool_registry import real_tool_registry

        caps = real_tool_registry().capabilities()
        return _reflex_answer(
            c,
            f"{_fa_num(len(caps))} قابلیت: " + "، ".join(caps),
        )

    # «امروز چی کار کردی؟ / امروز چه ساختی؟» — today's REAL runs, counted.
    if "امروز" in c and ("کار" in c or "ساختی" in c or "اجرا" in c or "کردی" in c):
        today = _query(
            db,
            "SELECT COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
            "WHERE date(created_at, 'localtime') = date('now', 'localtime') "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param'))",
        )
        n = int(today[0]["n"]) if today else 0
        n_ok = int(today[0]["ok_n"]) if today else 0
        if n == 0:
            return _reflex_answer(c, "امروز هنوز کاری انجام ندادهام — اولین فرمان را بده.")
        return _reflex_answer(
            c,
            f"امروز {_fa_num(n)} فرمان اجرا کردم؛ {_fa_num(n_ok)} موفق "
            f"({_fa_num(round(100 * n_ok / n) if n else 0)}٪).",
        )

    # R45-1 — TIME WINDOWS: «دیروز چی کار کردی؟» / «این هفته چطور بود؟» /
    # «ماه پیش چطور بود؟» — the same LOCAL-day law, three windows back.
    if any(w in c for w in ("دیروز", "هفته", "ماه پیش", "این ماه")) and (
        "کار" in c or "کردی" in c or "اجرا" in c or "چطور" in c or "بود" in c
    ):
        from universal_mind.time_windows import window_sentence

        for name in ("دیروز", "این هفته", "هفته پیش", "این ماه", "ماه پیش"):
            if name in c:
                try:
                    return _reflex_answer(c, window_sentence(name, db=db))
                except Exception:  # noqa: BLE001 — a time answer never crashes
                    return _reflex_answer(c, f"نمیتوانم {name} را از تاریخچه بخوانم.")

    # R45-3 — CHAT MEMORY: «آخرین گفتگویمان چه بود؟» — the REAL stored
    # conversation, replayed (up to 5 turns), with the same honest-zero law.
    if "گفتگو" in c and ("آخرین" in c or "چه بود" in c or "نشون" in c or "یادت" in c):
        from universal_mind.chat_history_store import message_count, recent_messages

        total_msgs = message_count()
        if total_msgs == 0:
            return _reflex_answer(c, "هنوز گفتگویی ثبت نشده — اولین کلمه را بگو.")
        msgs = recent_messages(5)
        if not msgs:
            return _reflex_answer(c, "گفتگو را نمیتوانم بخوانم.")
        _FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        lines = []
        for m in msgs:
            who = "من" if m["who"] == "من" else ("سیستم" if m["who"] == "سیستم" else m["who"])
            mark = "✅" if m["ok"] else ""
            lines.append(f"{who}: {m['text'][:80]}{' ' + mark if mark else ''}")
        return _reflex_answer(
            c,
            f"آخرین گفتگوی ما (از {str(total_msgs).translate(_FA)} پیام ثبتشده):\n"
            + "\n".join(lines),
        )

    # R45-12 — «چه واژههایی را نمیشناسی؟» — the harvest, read back.
    if "نمیشناس" in c and "واژه" in c:
        from universal_mind.unknown_harvest import unknown_sentence

        return _reflex_answer(c, unknown_sentence())

    # R45-11 — «پیشنهاد بده» — real advice from real runs.
    if "پیشنهاد" in c and ("بده" in c or "چی" in c or "کن" in c):
        from universal_mind.advisor_suggest import suggest

        info = suggest()
        return _reflex_answer(c, info["report"])

    # R45-10 — «وضعیت خودت چطور است؟» — five live signals, one answer.
    # R46-8 — FREE-FORM STATUS ASKS: «خب؟ / چی جدید؟ / وضع؟ / خبر چیست؟»
    # reach the SAME five-signal answer — the operator asks in whatever
    # shape comes to mind, the answer stays signal-carrying.
    if ("وضعیت خود" in c or "حالت خود" in c or ("سلامتی" in c and "خود" in c)
            or ("وضعیت" in c and "چطور" in c and "خود" in c)
            or c.strip().rstrip("?.!؟") in ("خب", "چی جدید", "وضع", "خبر چیست",
                                             "خبرها چیه", "چه خبرا", "وضعیت")):
        from universal_mind.self_status import self_status

        info = self_status()
        return _reflex_answer(c, info["report"])

    # R45-8 — THE WEEKLY LETTER, ASKED: «گزارش هفته چطور بود؟» reads the
    # letter the tick wrote (and if none is written yet, writes it NOW —
    # the answer is never a promise of a letter, it IS the letter).
    if "گزارش هفته" in c or "نامهی هفته" in c or ("گزارش" in c and "هفته" in c):
        from universal_mind.weekly_letter import latest_letter

        info = latest_letter()
        if not info.get("ok"):
            from universal_mind.weekly_letter import record_weekly_letter

            info = record_weekly_letter()
        return _reflex_answer(c, str(info.get("report", "")) or "نامهای نیست.")

    # «فایلهای ساختهشده امروز» — the artifacts of today's successes.
    if "فایل" in c and ("امروز" in c or "ساخته" in c or "درست کرده" in c):
        rows = _query(
            db,
            "SELECT command FROM run_history "
            "WHERE succeeded = 1 AND route != '' "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
            "AND date(created_at, 'localtime') = date('now', 'localtime') ORDER BY id DESC LIMIT 5",
        )
        if not rows:
            return _reflex_answer(c, "امروز فایلی ساخته نشده است.")
        names = [str(r["command"])[:30] for r in rows]
        return _reflex_answer(c, "کارهای موفق امروز: " + "؛ ".join(names) + ".")

    # «چند روز است زنده؟» — the REAL heartbeat history, not just "now".
    # (R44-13: the streak and the silent days, derived from the run store.)
    if (
        ("زنده" in c and ("چند" in c or "روز" in c or "است" in c))
        or ("تپش" in c and ("چند" in c or "وضع" in c or "چطور" in c or "چه" in c))
        or ("چند روزه" in c)
    ):
        from universal_mind.tick_pulse import pulse_report, pulse_sentence

        try:
            report = pulse_report(db=db)
        except Exception:  # noqa: BLE001 — a heartbeat answer never crashes
            return _reflex_answer(c, "نبضِ تپش را نتوانستم بخوانم.")
        return _reflex_answer(c, pulse_sentence(report))

    # «حافظهات چی میگن؟ / چی یاد گرفتی؟» — the REAL lessons, counted.
    if ("حافظه" in c or "یاد گرفتی" in c or "درس" in c) and (
        "میگن" in c or "گفته" in c or "چی" in c or "چه" in c or "یاد" in c
    ):
        try:
            rows = _query(db, "SELECT COUNT(*) AS n FROM planner_lessons")
            n = int(rows[0]["n"]) if rows else 0
            op_rows = _query(
                db,
                "SELECT operation, COUNT(*) AS n FROM planner_lessons "
                "GROUP BY operation ORDER BY n DESC LIMIT 3",
            )
            if not op_rows:
                return _reflex_answer(c, "هنوز درسی یاد نگرفتهام — چند فرمان بده تا بیاموزم.")
            top = "، ".join(
                f"{r['operation']} ({_fa_num(int(r['n']))} بار)" for r in op_rows
            )
            return _reflex_answer(
                c,
                f"{_fa_num(n)} درس ثبت کردهام؛ پرتکرارترین عملیاتها: {top}.",
            )
        except Exception:  # noqa: BLE001 — a reflex never crashes
            return _reflex_answer(c, "هنوز درسی یاد نگرفتهام — چند فرمان بده تا بیاموزم.")

    return None


def _store() -> DatabaseSuite:
    """The shared persistent store (R42: ONE truth for every reader).

    Tolerant of a lambda-mocked class (test isolation): falls back to the
    constructor the lambda understands.
    """
    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


def state_fa(state: str) -> str:
    return {"done": "✅ تمام", "stopped": "⏸ متوقف", "active": "▶ فعال"}.get(state, state)


def _reflex_answer(command: str, answer: str) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "route": ["reflexive"],
        "matched_words": ["پرسش"],
        "unknown": [],
        "extracted_params": {},
        "result": {"reflexive": {"answer": answer}},
        "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
        "agent_report": answer,
    }


__all__ = ["answer_reflexive", "state_fa"]