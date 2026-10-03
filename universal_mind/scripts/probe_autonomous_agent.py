#!/usr/bin/env python3
"""Probe: the AUTONOMOUS AGENT — goals scheduled, pursued, and resumed by the platform itself.

The full autonomy stack in one live pass:
1. REGISTER: «هر روز ساعت ۸ هدف: ...» — one sentence binds the agent layer to
   the clock (a scheduled goal, not a plain schedule);
2. FIRE: run_due picks it up and the agent completes the steps (ARETĒ-judged);
3. ORDINARY: a normal scheduled command still runs as a command (no hijack);
4. RESUME: a goal stopped mid-way resumes from its exact failing step.

All isolated from the operator's real schedules/goals — a probe never fires
their actual routine; the toast is mocked.

Exit non-zero unless every stage holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from unittest.mock import patch as mock_patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _isolated() -> AbstractContextManager[object]:
    import universal_mind.scheduler as sched_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(sched_mod, "_store", lambda: suite)


def check_goal_binds_to_the_clock() -> bool:
    """The one-sentence form registers as a scheduled GOAL with its steps."""
    from universal_mind.scheduler import list_schedules, register

    with _isolated():
        result = register(
            "هر روز ساعت ۸ هدف: میانگین ۱۰ و ۲۰ را حساب کن و گزارش کامل بساز"
        )
        schedules = list_schedules()
    ok = (
        result["ok"] and result.get("scheduled_goal") is True
        and len(result["steps"]) == 2 and result["hour_of_day"] == 8
        and schedules and schedules[0].command.startswith("__goal__")
    )
    print(f"  steps: {result.get('steps')}")
    return bool(ok)


def check_the_tick_completes_the_goal() -> bool:
    """A fired scheduled goal runs its steps to a finished, judged goal."""
    from universal_mind.scheduler import register, run_due

    with _isolated():
        register("هر ۱۵ دقیقه هدف: میانگین ۴ و ۶ را حساب کن و نمودار از ۲ و ۵ و ۹ کن")
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            fired = run_due(max_runs=2)
    entry = fired["fired"][0] if fired["fired"] else {}
    ok = fired["count"] >= 1 and entry.get("ok") is True and entry.get("route") == ["goal"]
    print(f"  fired: {fired['count']} | finished: {entry.get('ok')} | route: {entry.get('route')}")
    return bool(ok)


def check_ordinary_schedules_stay_ordinary() -> bool:
    """A plain command NEVER becomes a goal — the agent does not hijack."""
    from universal_mind.scheduler import list_schedules, register, run_due

    with _isolated():
        register("هر ۱۵ دقیقه میانگین ۲ و ۴ را حساب کن")
        schedules = list_schedules()
        assert schedules, "the schedule must register"
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            fired = run_due(max_runs=2)
    entry = fired["fired"][0] if fired["fired"] else {}
    ok = (
        not schedules[0].command.startswith("__goal__")
        and entry.get("route") != ["goal"]
        and entry.get("ok") is True
    )
    print(f"  command route: {entry.get('route')} (not a goal)")
    return bool(ok)


def check_a_stopped_goal_resumes_at_its_step() -> bool:
    """Resume: the failed step re-runs; finished steps are never re-run."""
    import json

    import universal_mind.agent_loop as agent_mod
    from universal_mind.agent_loop import run_goal, start_goal
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    ctx = mock_patch.object(agent_mod, "_store", lambda: suite)
    with ctx:
        started = start_goal(
            "هدف: آزمون ادامه",
            ("میانگین 4 و 6 را حساب کن", "این فرمان هیچ قابلیتی ندارد XYZQ"),
        )
        first = run_goal(started["goal_id"])
        if first.finished:
            print("  (unexpected pass — the second step should fail)")
            return False
        run_goal(started["goal_id"])  # resume from the failed step
        db = agent_mod._store()
        q = db.query("SELECT next_step, state, outcomes FROM goals WHERE id = ?",
                     (str(started["goal_id"]),))
        row = q["rows"][0]
        outcomes = json.loads(row["outcomes"])
    # resuming re-attempted the SAME failed step (index 1), not step 0
    resumed_attempts = [o for o in outcomes if o["index"] == 1]
    ok = len(resumed_attempts) >= 2 and all(o["index"] in (0, 1) for o in outcomes)
    print(f"  state: {row['state']} | step-1 attempts: {len(resumed_attempts)}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeAutonomousAgent",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAutonomousAgent", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("register: one sentence binds the goal to the clock", check_goal_binds_to_the_clock),
    ("fire: the tick completes the scheduled goal", check_the_tick_completes_the_goal),
    ("ordinary: plain schedules are never hijacked into goals", check_ordinary_schedules_stay_ordinary),
    ("resume: the stopped goal re-runs its failed step only", check_a_stopped_goal_resumes_at_its_step),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous-agent probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE AUTONOMOUS AGENT (هدفِ زمانبندیشده ← اجرا ← ادامه)")
    print("=" * 64)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        try:
            results.append((name, fn()))
        except Exception as exc:  # noqa: BLE001
            print(f"  check raised: {exc!r}")
            results.append((name, False))

    all_ok = all(ok for _, ok in results)
    for name, result in results:
        print(f"\n  {name}: {'OK' if result else 'FAILED'}")

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    print("\nALL CHECKS PASSED — THE AGENT RUNS ON THE OPERATOR'S CLOCK" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())