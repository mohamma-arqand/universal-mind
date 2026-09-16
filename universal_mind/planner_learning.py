"""Planner learning — the needs table earns its entries from real verdicts.

The dependency planner's needs table (which operation to pick when the sentence
is silent) was a fixed constant. This module makes it EARNED: after every real
run, the ARETĒ verdict for each (capability, operation) pair is folded into a
persistent record, and the planner consults that record BEFORE the static
default — a learned table beats a hardcoded one, and an unlearned pair falls
back honestly.

Honest rules:
- Only SUCCESSFUL runs teach (a failed operation never becomes advice).
- The learned mean excellence must MEET OR BEAT the static default's expected
  quality (0.75) to displace it — the learner must prove itself.
- Explicit sentence intent is NEVER overridden by learning (it only fills gaps).
- No record / no history → the static table, unchanged (never a guess).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.database_suite import DatabaseSuite

# The bar a learned operation must meet to displace the static default.
_LEARNED_BAR = 0.75


@dataclass(frozen=True)
class OperationLesson:
    """What history has taught about one (capability, operation) pair."""

    capability: str
    operation: str
    mean_excellence: float
    uses: int


def _store() -> DatabaseSuite:
    return DatabaseSuite(persistent=True)


def _ensure_table(db: DatabaseSuite) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS planner_lessons "
        "(capability TEXT, operation TEXT, excellence REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )


def teach(capability: str, operation: str, excellence: float, succeeded: bool) -> None:
    """Fold one real verdict into the lessons table (successes only teach)."""
    if not succeeded or operation is None or not operation:
        return  # a failed run teaches nothing
    if excellence is None:
        return
    db = _store()
    _ensure_table(db)
    db.insert_many(
        "planner_lessons",
        [{"capability": capability, "operation": operation, "excellence": f"{excellence:.4f}"}],
    )


def learned_operations(capability: str) -> list[OperationLesson]:
    """The operations history has proven for this capability, best first."""
    db = _store()
    _ensure_table(db)
    q = db.query(
        "SELECT operation, AVG(excellence) AS m, COUNT(*) AS n FROM planner_lessons "
        "WHERE capability = ? GROUP BY operation ORDER BY m DESC, n DESC",
        (capability,),
    )
    if not q.get("ok"):
        return []
    lessons: list[OperationLesson] = []
    for row in q.get("rows", []):
        try:
            mean = float(row["m"])
        except (TypeError, ValueError):
            continue
        lessons.append(
            OperationLesson(
                capability=capability,
                operation=str(row["operation"]),
                mean_excellence=round(mean, 4),
                uses=int(row["n"]),
            )
        )
    return lessons


def best_learned_operation(capability: str, bar: float = _LEARNED_BAR) -> OperationLesson | None:
    """The best PROVEN operation for this capability, or None (never a guess).

    A lesson displaces the static default only when its mean excellence meets
    the bar — the learner must prove itself, not merely exist.
    """
    lessons = learned_operations(capability)
    for lesson in lessons:
        if lesson.mean_excellence >= bar:
            return lesson
    return None


def lessons_report() -> dict[str, Any]:
    """The learned table, human-readable (for the analytics tab)."""
    db = _store()
    _ensure_table(db)
    q = db.query(
        "SELECT capability, operation, AVG(excellence) AS m, COUNT(*) AS n "
        "FROM planner_lessons GROUP BY capability, operation ORDER BY capability, m DESC"
    )
    if not q.get("ok"):
        return {"lessons": []}
    rows = [
        {
            "capability": str(r["capability"]),
            "operation": str(r["operation"]),
            "mean_excellence": round(float(r["m"]), 4),
            "uses": int(r["n"]),
        }
        for r in q.get("rows", [])
        if r.get("m") is not None
    ]
    return {"lessons": rows}


__all__ = [
    "OperationLesson",
    "best_learned_operation",
    "learned_operations",
    "lessons_report",
    "teach",
]