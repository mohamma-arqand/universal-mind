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

    # Greetings — the first word anyone says.
    if c in ("سلام", "درود", "سلام علیکم", "هلو", "hi", "hello"):
        return _say(c, "سلام! چه کارهایی برایت انجام دهم؟")
    if c in ("خسته نباشید", "خسته نباشی", "ممنون", "مرسی", "سپاس", "thanks", "thank you"):
        return _say(c, "خواهش میکنم! کاری بود، فرمان بده.")
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