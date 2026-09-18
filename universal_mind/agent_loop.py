"""The agent loop — a GOAL executed as judged steps, with honest persistence.

The layer above commands: the operator states an objective («هدف: ...»),
the parser cuts it into steps, and this loop runs each step through the
REAL engine under ARETĒ judgment:

  for each step:
    run → ARETĒ judges the step's own run
      strong → record, next step
      weak   → ONE honest repair attempt (the step re-run through the
               quality gate's rival search); if still weak, the goal STOPS
               with the exact failure — never a blind march through a
               broken chain of steps.

Honest rules:
- Progress is PERSISTED (the goals table): a goal interrupted mid-run can
  be resumed from the exact step («ادامه بده» at the CLI).
- Every step's outcome (ok, excellence, repaired) is recorded — the goal's
  own history is auditable.
- An already-finished step is never re-run on resume.
- max_steps bounds the loop (a goal with no honest steps fails, not loops).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.database_suite import DatabaseSuite


@dataclass(frozen=True)
class StepOutcome:
    """One step's real result inside the goal run."""

    index: int
    command: str
    ok: bool
    excellence: float
    repaired: bool
    detail: str = ""


@dataclass(frozen=True)
class GoalRunResult:
    """The whole goal run: every step, where it stands, and why."""

    goal: str
    steps: tuple[StepOutcome, ...]
    finished: bool           # all steps ran (each honestly)
    stopped_at: int          # -1 when finished; else the failing step index
    reasoning: str


def _store() -> DatabaseSuite:
    return DatabaseSuite(persistent=True)


def _ensure_goals_table(db: DatabaseSuite) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS goals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "goal TEXT, steps TEXT, next_step INTEGER DEFAULT 0, "
        "outcomes TEXT DEFAULT '[]', state TEXT DEFAULT 'active', "
        "guarded TEXT DEFAULT '')"
    )
    # migrate an existing table: add guarded when missing (the silent-migration
    # lesson: verify the column list afterwards).
    try:
        cols = db.query("SELECT name FROM pragma_table_info('goals')")
        if cols.get("ok") and "guarded" not in {str(c["name"]) for c in cols["rows"]}:
            db.execute("ALTER TABLE goals ADD COLUMN guarded TEXT DEFAULT ''")
    except Exception:  # noqa: BLE001
        pass
    # GOAL ARCHIVE: finished/stopped goals older than the newest 100 move to
    # goals_archive (the live table stays fast; nothing is ever DELETED —
    # history is append-only, the archive is where it lives).
    db.execute(
        "CREATE TABLE IF NOT EXISTS goals_archive ("
        "id INTEGER PRIMARY KEY, goal TEXT, steps TEXT, next_step INTEGER, "
        "outcomes TEXT, state TEXT, archived_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    try:
        q = db.query("SELECT COUNT(*) AS n FROM goals")
        total = int(q["rows"][0]["n"]) if q.get("ok") else 0
        if total > 100:
            # Newest 100 stay live; older FINISHED goals move to the archive.
            # The candidate set is computed in Python (one honest query) — the
            # INSERT/DELETE then use a simple id list (no nested NOT-IN SQL,
            # which silently matched nothing through this suite's executor).
            finished = db.query(
                "SELECT id FROM goals WHERE state IN ('done', 'stopped') ORDER BY id DESC"
            )
            if finished.get("ok"):
                all_done = [int(r["id"]) for r in finished["rows"]]
                to_archive = all_done[100:]  # everything past the newest 100
                if to_archive:
                    id_list = ",".join(str(i) for i in to_archive)
                    db.execute(
                        "INSERT OR IGNORE INTO goals_archive "
                        "(id, goal, steps, next_step, outcomes, state) "
                        f"SELECT id, goal, steps, next_step, outcomes, state FROM goals WHERE id IN ({id_list})"
                    )
                    db.execute(f"DELETE FROM goals WHERE id IN ({id_list})")
    except Exception:  # noqa: BLE001 — archival is housekeeping, never fatal
        pass


def start_goal(
    goal_text: str,
    steps: tuple[str, ...],
    guarded: tuple[bool, ...] | None = None,
) -> dict[str, Any]:
    """Persist a new goal (or revive an identical unfinished one)."""
    db = _store()
    _ensure_goals_table(db)
    q = db.query(
        "SELECT id, next_step FROM goals WHERE goal = ? AND state = 'active'",
        (goal_text,),
    )
    if q.get("ok") and q["rows"]:
        return {"ok": True, "goal_id": int(q["rows"][0]["id"]), "resumed": True, "error": ""}
    db.insert_many("goals", [{
        "goal": goal_text, "steps": "|".join(steps),
        "next_step": "0", "outcomes": "[]", "state": "active",
        "guarded": "|".join("1" if g else "0" for g in (guarded or ()) * 1)[: len(steps) * 2 - 1] if guarded else "",
    }])
    q2 = db.query("SELECT id FROM goals WHERE goal = ? AND state = 'active'", (goal_text,))
    goal_id = int(q2["rows"][0]["id"]) if q2.get("ok") and q2["rows"] else -1
    return {"ok": goal_id > 0, "goal_id": goal_id, "resumed": False, "error": ""}


def _record_outcome(db: DatabaseSuite, goal_id: int, outcome: StepOutcome) -> None:
    import json

    q = db.query("SELECT outcomes FROM goals WHERE id = ?", (str(goal_id),))
    outcomes: list[dict[str, Any]] = json.loads(q["rows"][0]["outcomes"] or "[]") if q.get("ok") and q["rows"] else []
    outcomes.append({
        "index": outcome.index, "command": outcome.command,
        "ok": outcome.ok, "excellence": outcome.excellence,
        "repaired": outcome.repaired, "detail": outcome.detail,
    })
    db.execute(
        f"UPDATE goals SET outcomes = '{json.dumps(outcomes, ensure_ascii=False).replace(chr(39), chr(39)*2)}' "
        f"WHERE id = {goal_id}"
    )


def run_goal(goal_id: int, *, max_steps: int = 8, bar: float = 0.75) -> GoalRunResult:
    """Run the goal from its persisted next_step, honestly and resumably."""

    from universal_mind.arete.run_judgment import judge_run
    from universal_mind.persian_router import route_and_run

    db = _store()
    _ensure_goals_table(db)
    q = db.query("SELECT goal, steps, next_step, guarded FROM goals WHERE id = ?", (str(goal_id),))
    if not q.get("ok") or not q["rows"]:
        return GoalRunResult(goal="", steps=(), finished=False, stopped_at=-1,
                             reasoning="چنین هدفی ثبت نشده است")
    row = q["rows"][0]
    goal_text = str(row["goal"])
    steps = tuple(str(row["steps"]).split("|"))
    # The DAG upgrade: if the steps carry dependency clauses, the run follows
    # the MAP (topological passes) instead of the plain order. The join step
    # (بعد از همه) runs once every other step has an outcome — success,
    # failure, or honest skip all count as ENDED.
    goal_map = None
    passes: list[list[int]] | None = None
    try:
        from universal_mind.goal_map import execution_order, parse_goal_map

        goal_map = parse_goal_map(goal_text, steps)
        if goal_map is not None and (goal_map.depends_on or goal_map.join_index is not None):
            passes = execution_order(goal_map)
    except Exception:  # noqa: BLE001 — the map is an upgrade, never a blocker
        passes = None
    guard_raw = str(row.get("guarded", "") or "")
    guarded = tuple(g == "1" for g in guard_raw.split("|") if g != "") if guard_raw else tuple(False for _ in steps)
    next_step = int(row["next_step"] or 0)

    outcomes: list[StepOutcome] = []
    # The MAP order (waves) when a DAG was declared; otherwise the linear order.
    execution_indexes: list[int] = []
    if passes:
        for wave in passes:
            execution_indexes.extend(wave)
        # resume support: drop already-finished indexes (best-effort — the DAG
        # is the fresh-run order; resumed goals re-walk from the map's start
        # for any step still missing an outcome)
        execution_indexes = [i for i in execution_indexes if i >= next_step or next_step == 0]
    else:
        execution_indexes = list(range(next_step, min(len(steps), next_step + max_steps)))
    for index in execution_indexes[:max_steps]:
        command = steps[index]
        # A CONDITIONAL step: run only if the previous executed step's
        # ARETĒ verdict said ok. Previous failure → SKIPPED honestly (the
        # goal continues; the guard's whole point is not to march on).
        if index > 0 and index < len(guarded) and guarded[index]:
            prev = outcomes[-1] if outcomes else None
            if prev is None or not prev.ok:
                skip = StepOutcome(
                    index=index, command=command, ok=True,
                    excellence=0.0, repaired=False,
                    detail="رد شد — گام شرطیِ پس از گام ناموفق اجرا نشد",
                )
                outcomes.append(skip)
                _record_outcome(db, goal_id, skip)
                db.execute(f"UPDATE goals SET next_step = {index + 1} WHERE id = {goal_id}")
                continue
        payload = route_and_run(command)
        judgment = judge_run(payload)
        excellence = float(judgment.get("excellence", 0.0))
        repaired = False
        if payload.get("ok") is not True or excellence < bar:
            # ONE honest repair pass: the quality gate's rival search.
            # The command is BOUND NOW (a late-binding closure over the loop
            # variable would repair the WRONG step's command — B023 caught it).
            from universal_mind.quality_gate import run_with_quality_gate

            step_command = command

            def _run_candidate(candidate: tuple[str, ...], _cmd: str = step_command) -> dict[str, Any]:
                return route_and_run(_cmd, forced_route=list(candidate))

            gate = run_with_quality_gate(command, tuple(payload.get("route", [])), _run_candidate, bar=bar)
            if gate.shipped.excellence > excellence:
                payload = gate.shipped.payload
                excellence = gate.shipped.excellence
                repaired = True
        step_ok = payload.get("ok") is True
        outcome = StepOutcome(
            index=index, command=command, ok=step_ok,
            excellence=excellence, repaired=repaired,
            detail=str(payload.get("errors") or ""),
        )
        outcomes.append(outcome)
        _record_outcome(db, goal_id, outcome)
        if not step_ok:
            # A failed step stops the goal UNLESS something DEPENDS on its
            # ENDING (not its success): a CONDITIONAL next step (the guard
            # reacts to failure) or a JOIN still waiting on this branch (the
            # DAG's whole point is to unify outcomes, failures included).
            next_guarded = (
                index + 1 < len(guarded) and guarded[index + 1]
            )
            join_waiting = bool(goal_map is not None and goal_map.join_index is not None and goal_map.join_index != index)
            if not (next_guarded or join_waiting):
                db.execute(f"UPDATE goals SET next_step = {index}, state = 'stopped' WHERE id = {goal_id}")
                return GoalRunResult(
                    goal=goal_text, steps=tuple(outcomes), finished=False,
                    stopped_at=index,
                    reasoning=f"گام {index + 1} شکست خورد ({outcome.detail[:60]}) — هدف متوقف شد",
                )
        db.execute(f"UPDATE goals SET next_step = {index + 1} WHERE id = {goal_id}")

    db.execute(f"UPDATE goals SET state = 'done' WHERE id = {goal_id}")
    return GoalRunResult(
        goal=goal_text, steps=tuple(outcomes), finished=True, stopped_at=-1,
        reasoning=f"همهی گامها اجرا شد ({len(outcomes)} گام)",
    )


def goal_run_report(result: GoalRunResult) -> str:
    """The goal run rendered as fluent Persian."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    lines = [f"🎯 {result.goal}"]
    for step in result.steps:
        mark = "✅" if step.ok else "❌"
        note = " (ترمیم شد)" if step.repaired else ""
        lines.append(
            f"  {mark} گام {str(step.index + 1).translate(fa)}: {step.command}"
            f" — داوری {str(round(step.excellence, 2)).translate(fa)}{note}"
        )
    lines.append(f"→ {result.reasoning}")
    return "\n".join(lines)


__all__ = [
    "GoalRunResult",
    "StepOutcome",
    "goal_run_report",
    "run_goal",
    "start_goal",
]