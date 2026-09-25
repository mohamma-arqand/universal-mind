"""The operator's verdict — the human judge joins the learning loops.

R44 item 3: «عالی بود» / «بد بود» after a run records the OPERATOR's own
verdict, bound to that run's route and excellence. A negative verdict is
a real down-rank signal for the advisor (the human's word outranks
history's raw count), a positive one reinforces.

STANDARDS:
- The verdict binds to the LAST real run of that command (never a guess).
- The advisor consumes verdicts as a multiplicative weight.
- Never a crash: a verdict on an empty history answers honestly.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite


def _store() -> DatabaseSuite:
    """The shared persistent store (lambda-mock tolerant)."""
    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


def record_verdict(command: str, verdict: str) -> dict[str, Any]:
    """Record the operator's verdict for the LAST REAL run of this command.

    verdict: 'good' | 'bad'. The row binds to the newest run of the same
    command that was not a question (needs_param) nor an env refusal.
    """
    c = command.strip()
    v = "good" if verdict in ("good", "عالی", "خوب") else "bad"
    db = _store()
    db.execute(
        "CREATE TABLE IF NOT EXISTS operator_verdicts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT NOT NULL, route TEXT NOT NULL, "
        "verdict TEXT NOT NULL, created_at TEXT NOT NULL)",
        # R46-11 — the verdict-date index: the advisor filters by time.
        "CREATE INDEX IF NOT EXISTS idx_verdicts_created ON operator_verdicts (created_at)",
    )
    rows = db.query(
        "SELECT route FROM run_history WHERE command = ? AND succeeded = 1 "
        "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
        "ORDER BY id DESC LIMIT 1",
        (c,),
    ).get("rows", [])
    if not rows:
        return {
            "ok": False,
            "answer": "هنوز اجرای موفقی از این فرمان ندارم تا رأی رویش بنشیند — اول اجرایش کن.",
        }
    route = str(rows[0]["route"])
    from datetime import datetime

    db.insert_many(
        "operator_verdicts",
        [{"command": c, "route": route, "verdict": v,
          "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}],
    )
    if v == "good":
        answer = "شنیدم و یاد گرفتم — این زنجیره را بیشتر پیش میآورم."
        # R46-3 — THE VERDICT BECOMES A LAW: the approved command's REAL
        # report promises are captured as drift anchors, so a future
        # regression on THIS command turns the gate red BY NAME.
        try:
            from universal_mind.report_laws import record_law

            law = record_law(c, _last_report_for(c))
            if law.get("ok"):
                answer += " و قوانینش را در پایشِ رانش نگه داشتم."
        except Exception:  # noqa: BLE001 — the law is a lens, never fatal
            pass
    else:
        answer = "شنیدم؛ این زنجیره را در انتخابهای بعدی پایین میآورم و جایگزین بهتری میآزم."
    return {"ok": True, "verdict": v, "route": route, "answer": answer}


def _last_report_for(command: str) -> str:
    """The newest stored FULL report for a command (run_reports), or ''.

    R46-3: the anchors must come from the REAL report text — the run's own
    rendered promises — never from the command string itself.
    """
    try:
        from universal_mind.report_laws import last_report

        return last_report(command)
    except Exception:  # noqa: BLE001 — best-effort anchor capture
        return ""


def route_weight(route: tuple[str, ...]) -> float:
    """The human-weight of a route: 1.0 neutral, down per 'bad', up per 'good'.

    The operator's word outranks raw counts: each bad verdict multiplies by
    0.5, each good by 1.25 — clamped to [0.05, 2.0].
    """
    db = _store()
    try:
        rows = db.query(
            "SELECT verdict, COUNT(*) AS n FROM operator_verdicts "
            "WHERE route = ? GROUP BY verdict",
            (",".join(route),),
        ).get("rows", [])
    except Exception:  # noqa: BLE001 — a lens, never a blocker
        return 1.0
    weight = 1.0
    for r in rows:
        n = int(r["n"])
        if str(r["verdict"]) == "bad":
            weight *= 0.5 ** n
        elif str(r["verdict"]) == "good":
            weight *= 1.25 ** n
    return max(0.05, min(2.0, weight))


def is_verdict_phrase(command: str) -> bool:
    """«عالی بود» / «بد بود» / «خوب نبود» — the operator is RULING."""
    c = command.strip()
    return c in (
        "عالی بود", "بد بود", "خوب نبود", "خوب بود", "عالی بود!",
        "بد بود!", "ایول", "افتضاح بود",
    ) or c.startswith(("عالی بود", "بد بود", "خوب نبود"))


__all__ = ["record_verdict", "route_weight", "is_verdict_phrase"]
