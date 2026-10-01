"""The conversational class — the operator's SMALL TALK gets an answer.

«سلام» / «خسته نباشید» / «ممنون» / «کمک کن» / «دنبال چه میگردی؟» fell
through every route to empty — a platform that answers statistics questions
but goes mute on «سلام» feels broken at the FIRST word the operator says.

This is NOT a capability run: it reads the session's live state and answers
in fluent Persian, warm and short. The face of the platform, not its tools.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa_num(v: int | float | str) -> str:
    return str(v).translate(_FA)


def _store() -> DatabaseSuite:
    """The shared persistent store (R42) — lambda-mock tolerant."""
    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


def _recent_activity() -> str:
    """One honest line about what the platform has been doing."""
    db = _store()
    try:
        q = db.query(
            "SELECT command FROM run_history WHERE succeeded = 1 AND route != '' "
            "AND outcome_class IS NOT 'blocked_env' ORDER BY id DESC LIMIT 1"
        )
        rows = q.get("rows", []) if q.get("ok") else []
        if not rows:
            return "هنوز چیزی نساختهام — یک فرمان بده."
        return f"آخرین کارم: «{rows[0]['command'][:40]}»."
    except Exception:  # noqa: BLE001 — small talk never crashes the router
        return ""


def answer_conversational(command: str) -> dict[str, Any] | None:
    """Route small talk to a warm, SHORT, state-aware answer — or None.

    None = not small talk; the ordinary router continues. Matched, it NEVER
    runs a capability — it answers, in the operator's own tone.
    """
    c = command.strip()

    # Greetings — the first word anyone says. R46-5: the greeting is
    # STATE-AWARE — it knows what the platform is holding FOR the
    # operator right now (active goals, today's reminders, today's runs)
    # and offers them by name. A secretary who says only «سلام» wastes
    # the most valuable moment of the conversation.
    if c in ("سلام", "درود", "سلام علیکم", "هلو", "hi", "hello"):
        return _say(c, _greeting_state())
    if c in ("خسته نباشید", "خسته نباشی", "ممنون", "متشکرم", "تشکر", "مرسی",
             "سپاس", "سپاسگزارم", "thanks", "thank you"):
        return _say(c, "خواهش میکنم! کاری بود، فرمان بده.")
    # R60 Q6 — «حال شما چطوره؟» — the social question. The answer is honest
    # about what the platform is (no fake feelings): state-aware, one line.
    if c in ("حال شما چطوره؟", "حال شما چطوره", "حالت چطوره؟", "حالت چطوره",
             "حال شما چطور است؟", "حال چطوره؟", "خوبی؟", "چطوری؟"):
        return _say(c, "سالم و آماده‌ام — " + _status_answer())
    # R53 wave-3 — IDENTITY: who am I, what can I do, how am I. A platform
    # that answers statistics but goes mute on «اسمت چیه؟» has no face.
    if c in ("اسمت چیه؟", "اسمت چیست؟", "اسم تو چیه؟", "اسمت؟") or "اسمت" in c and "چی" in c:
        return _say(c, "اسمم «ذهن جهانی» است — دستیار فارسیزبانِ همین سیستم.")
    if ("کی هستی" in c or "کیستی" in c or "خودت را معرفی" in c or "معرفی کن" in c):
        return _say(c, _identity_intro())
    if ("وضعیتت" in c or "وضعیت تو" in c) and ("چطور" in c or "چیه" in c or "چطوره" in c or "?" in c or "؟" in c):
        return _say(c, _status_answer())
    if ("چه کارهایی بلدی" in c or "چیکار میتونی بکنی" in c or "چه کارها میتونی" in c
            or "چه کارهایی میتونی" in c or "چی بلدی" in c or "چه بلدی" in c
            or "قابلیتهات" in c or "قابلیت هات" in c):
        return _say(c, _abilities_answer())
    if ("چه یاد گرفتی" in c or "چه چیزهایی یاد گرفتی" in c
            or "یادگیریهایت" in c):
        try:
            from universal_mind.learned_vocab import learned_words

            learned = learned_words()
        except Exception:  # noqa: BLE001 — the learner is a lens
            learned = []
        if learned:
            parts = "، ".join(f"«{d['word']}»→{d['capability']}" for d in learned[:6])
            return _say(c, f"اینها را از تو یاد گرفتم: {parts}.")
        return _say(c, "هنوز واژهای به من یاد ندادهی — با «واژهی X یعنی Y» یادم بده.")
    if c in ("دنبال چه میگردی؟", "چیکار میکنی؟", "چه خبر؟", "حالت چطوره؟"):
        line = _recent_activity()
        return _say(c, f"در خدمتم — {line}" if line else "در خدمتم؛ منتظر فرمانت هستم.")
    if c in ("کمک کن", "کمک کن لطفا", "راهنمایی کن", "help") or (
        "کمک" in c and ("چی کار" in c or "چیکار" in c)
    ):
        return _say(
            c,
            "با فرمان ساده کار میکنم: «نمودار بکش»، «میانگین ۳ و ۹ را حساب کن»، "
            "«گزارش بساز»، «چه کارهایی میتونی بکنی؟» برای فهرست کامل.",
        )
    # Farewells — the LAST word anyone says deserves an answer too.
    if c in ("خدانگهدار", "خداحافظ", "خدانگهدار!", "بای", "bye", "فعلاً", "فعلا") or c.startswith("خدانگهدار") or c.startswith("خداحافظ"):
        return _say(c, "خدانگهدار! منتظر بازگشتت هستم — هر وقت فرمان داشتی، من اینجام.")
    # Smalltalk prefixes — answer briefly rather than routing to nothing.
    if c.startswith("سلام ") or "خوبی؟" in c:
        return _say(c, "سلام! فرمانت را بگو.")
    return None


def _identity_intro() -> str:
    """«تو کی هستی؟» — a three-sentence state-aware introduction."""
    parts = ["من «ذهن جهانی» هستم؛ یک دستیار فارسیزبان که روی همین سیستم زندگی میکند."]
    try:
        from universal_mind.real_tool_registry import real_tool_registry

        n_caps = len(real_tool_registry().capabilities())
        parts.append(f"{_fa_num(n_caps)} قابلیت واقعی دارم؛ از نمودار و سند تا گفتار و یادآور.")
    except Exception:  # noqa: BLE001 — the face never crashes
        parts.append("از نمودار و سند تا گفتار و یادآور، با ابزار واقعی کار میکنم.")
    parts.append("فرمانت را فارسی بگو؛ اگر چیزی را نشناختم، صادقانه میگویم.")
    return " ".join(parts)


def _status_answer() -> str:
    """«وضعیتت چطوره؟» — the honest five-signal summary, one line each."""
    try:
        from universal_mind.self_status import self_status

        rep = str(self_status().get("report", ""))
        return rep if rep else "همهچیز روشن است؛ فرمانت را بگو."
    except Exception:  # noqa: BLE001
        return "در خدمتم — فرمانت را بگو."


def _abilities_answer() -> str:
    """«چه کارهایی بلدی؟» — the counted capability list + 3 live examples."""
    try:
        from universal_mind.real_tool_registry import real_tool_registry

        caps = real_tool_registry().capabilities()
        head = f"{_fa_num(len(caps))} قابلیت: " + "، ".join(sorted(caps))
    except Exception:  # noqa: BLE001
        return "برای فهرست کامل، «راهنما» بگو."
    examples = (
        "\nنمونه: «نمودار بکش»، «میانگین ۳ و ۹ را حساب کن»، «یادم بنداز فردا ساعت ۸ بیدارم کن»."
    )
    return head + examples


def _greeting_state() -> str:
    """«سلام» that knows what it is holding: goals, reminders, today."""
    parts: list[str] = ["سلام!"]
    try:
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite.shared_persistent()
        today = db.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE date(created_at) = date(datetime('now', 'localtime'))"
        )
        n_today = int(today["rows"][0]["n"]) if today.get("ok") and today.get("rows") else 0
        goals = db.query("SELECT COUNT(*) AS n FROM goals WHERE state = 'active'")
        n_goals = int(goals["rows"][0]["n"]) if goals.get("ok") and goals.get("rows") else 0
        paused = db.query("SELECT COUNT(*) AS n FROM goals WHERE state = 'paused'")
        n_paused = int(paused["rows"][0]["n"]) if paused.get("ok") and paused.get("rows") else 0
    except Exception:  # noqa: BLE001 — the greeting is a courtesy, never fatal
        return "سلام! چه کارهایی برایت انجام دهم؟"

    label = "امروز"  # the R45 local-day label (window names live in time_windows)
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    bits: list[str] = []
    if n_goals:
        bits.append(f"{str(n_goals).translate(fa)} هدف فعال")
    if n_paused:
        bits.append(f"{str(n_paused).translate(fa)} هدف در انتظار تصمیمت (بگو: ادامه بده / بایست)")
    if n_today:
        bits.append(f"{label} {str(n_today).translate(fa)} فرمان اجرا کردیم")
    if bits:
        parts.append(" — " + "، ".join(bits) + ".")
    parts.append(" چه کار کنم؟")
    return "".join(parts)


def _say(command: str, answer: str) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "route": ["conversational"],
        "matched_words": ["گفتار"],
        "unknown": [],
        "extracted_params": {},
        "result": {"conversational": {"answer": answer}},
        "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
        "agent_report": answer,
    }


__all__ = ["answer_conversational"]