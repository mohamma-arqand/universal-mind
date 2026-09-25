"""«پیشنهاد بده» — advice from what the operator ACTUALLY does.

R45 item 11: 34k real runs are a goldmine nobody reads in conversation.
This module derives the advice from the real store (LOCAL-day law,
unknown-noise excluded):

  hot      — the route(s) the operator used most this week (a real habit)
  best     — the highest-excellence successful route of the last 30 days
  never    — capabilities in the router's vocabulary that appear in NO
             successful run at all — named, so the operator knows what
             they are missing, never more than three (advice is a nudge,
             not a lecture)

An empty store says «هنوز چیزی برای پیشنهاد ندارم» — never a fabricated
suggestion.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_EXCLUDE = (
    "(outcome_class IS NULL OR outcome_class NOT IN "
    "('blocked_env', 'needs_param', 'unknown_noise'))"
)

# The advisory vocabulary: capability -> the Persian sentence that names it.
_NEVER_USED_HINT: dict[str, str] = {
    "speech": "«بگو» تا متن را با صدای بلند بخوانم",
    "hearing": "«گوش کن» تا حرفت را بشنوم و اجرا کنم",
    "email": "«ایمیل بفرست به ...» تا نامه را واقعا بفرستم",
    "excel": "«اکسل بساز» تا جدول فارسی و راستبهچپ تحویل بگیری",
    "clipboard": "«کپی کن» تا متن در کلیپبوردت بنشیند",
    "ocr": "«متن عکس را بخوان» تا تصویر را به متن تبدیل کنم",
    "stt": "«گوش کن» تا صدایت را متن کنم",
    "webfetch": "«دانلود کن ...» تا صفحهی وب را واقعا بگیرم",
}


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def _hot_routes(db: DatabaseSuite, limit: int = 2) -> list[tuple[str, int]]:
    q = db.query(
        "SELECT route, COUNT(*) AS n FROM run_history "
        "WHERE date(created_at, 'localtime') >= date('now', 'localtime', '-6 day') "
        f"AND route != '' AND {_EXCLUDE} "
        "GROUP BY route ORDER BY n DESC LIMIT ?",
        (limit,),
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return [(str(r["route"]), int(r["n"])) for r in rows]


def _best_route(db: DatabaseSuite) -> tuple[str, float] | None:
    q = db.query(
        "SELECT route, AVG(excellence) AS m FROM run_history "
        "WHERE date(created_at, 'localtime') >= date('now', 'localtime', '-30 day') "
        f"AND succeeded = 1 AND route != '' AND excellence != '' AND {_EXCLUDE} "
        "GROUP BY route ORDER BY m DESC LIMIT 1",
    )
    rows = q.get("rows", []) if q.get("ok") else []
    if not rows:
        return None
    return str(rows[0]["route"]), float(rows[0]["m"])


def _never_used(db: DatabaseSuite, limit: int = 3) -> list[str]:
    q = db.query(
        "SELECT DISTINCT route FROM run_history WHERE succeeded = 1 AND route != ''"
    )
    used = {str(r["route"]) for r in (q.get("rows", []) if q.get("ok") else [])}
    # routes are comma-joined chains — a capability counts as used if it
    # appears in ANY successful chain
    used_caps = {cap.strip() for chain in used for cap in chain.split(",") if cap.strip()}
    hints = []
    for cap, hint in _NEVER_USED_HINT.items():
        if cap not in used_caps:
            hints.append(hint)
        if len(hints) >= limit:
            break
    return hints


def suggest(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Real advice from real runs — hot habits, the best route, the unknowns."""
    store = db or DatabaseSuite.shared_persistent()

    total_q = store.query(
        f"SELECT COUNT(*) AS n FROM run_history WHERE {_EXCLUDE}"
    )
    rows = total_q.get("rows", []) if total_q.get("ok") else []
    total = int(rows[0]["n"]) if rows else 0
    if total == 0:
        return {
            "ok": True, "hot": [], "best": None, "never": [],
            "report": "هنوز چیزی برای پیشنهاد ندارم — چند فرمان بده تا سلیقهات را بشناسم.",
            "error": "",
        }

    hot = _hot_routes(store)
    best = _best_route(store)
    never = _never_used(store)

    parts: list[str] = []
    if hot:
        hot_txt = " و ".join(f"«{r}» ({_fa(n)} بار)" for r, n in hot)
        parts.append(f"این روزها بیشتر {hot_txt} میخواهی")
    if best:
        parts.append(f"مسیرِ باکیفیتِ اخیرت «{best[0]}» بوده (داوری {_fa(round(best[1] * 100))}٪)")
    if never:
        parts.append("اینها را هم امتحان کن: " + "؛ ".join(never))
    report = "پیشنهاد من:\n" + "\n".join(f"• {p}." for p in parts) if parts else (
        "تاریخچهات سرشار است — مسیرهایت را ادامه بده."
    )
    return {"ok": True, "hot": hot, "best": best, "never": never,
            "report": report, "error": ""}
