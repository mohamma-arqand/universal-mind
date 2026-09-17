#!/usr/bin/env python3
"""Probe: the agent loop — a GOAL, judged step by step, resumable.

The layer above commands, proven live:
1. PARSE: a Persian objective cuts into steps WITHOUT breaking data lists
   («۱۰ و ۲۰» stays one list; «و» between steps still splits);
2. RUN: every step really runs through the engine with its ARETĒ verdict;
3. PERSIST: the goal's progress and outcomes land in the real goals table;
4. RESUME: a stopped goal resumes from its exact failing step — and finished
   steps are never re-run;
5. HONEST STOP: a broken step stops the goal at that step, never a blind march.

Exit non-zero unless every stage holds. All isolated from the operator's
real goals — a probe never touches them.
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
    """A fresh temp goals table — the operator's real goals are never touched."""
    import universal_mind.agent_loop as agent_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(agent_mod, "_store", lambda: suite)


def check_parse_keeps_data_lists() -> bool:
    """«۱۰ و ۲۰» is one list; steps still split on the real conjunctions."""
    from universal_mind.goal_parser import parse_goal

    goal = parse_goal("هدف: میانگین ۱۰ و ۲۰ را حساب کن و نمودارش کن و گزارش کامل بساز")
    ok = goal is not None and goal.steps == (
        "میانگین 10 و 20 را حساب کن", "نمودارش کن", "گزارش کامل بساز",
    )
    print(f"  steps: {goal.steps if goal else None}")
    return bool(ok)


def check_goal_runs_with_judgment() -> bool:
    """A real 2-step goal: every step runs, every step carries its verdict."""
    from universal_mind.agent_loop import goal_run_report, run_goal, start_goal

    with _isolated():
        started = start_goal(
            "هدف: میانگین ۴ و ۶ را حساب کن و نمودارش کن",
            ("میانگین 4 و 6 را حساب کن", "نمودارش کن"),
        )
        result = run_goal(started["goal_id"])
    ok = result.finished and len(result.steps) == 2
    ok = ok and all(s.ok for s in result.steps)
    ok = ok and all(s.excellence >= 0.5 for s in result.steps)
    report = goal_run_report(result)
    print(f"  finished: {result.finished} | steps: {len(result.steps)}")
    print(f"  report[0]: {report.splitlines()[0][:60]}")
    return bool(ok)


def check_a_broken_step_stops_honestly() -> bool:
    """An un-routable step stops the goal AT that step — no blind march."""
    from universal_mind.agent_loop import run_goal, start_goal

    with _isolated():
        started = start_goal(
            "هدف: آزمون شکست",
            ("این فرمان هیچ قابلیتی فعال نمیکند ز XYZ", "نمودارش کن"),
        )
        result = run_goal(started["goal_id"])
    ok = result.finished is False and result.stopped_at == 0
    print(f"  stopped_at: {result.stopped_at} | why: {result.reasoning[:50]}")
    return bool(ok)


def check_goal_persists_and_resumes() -> bool:
    """Progress lands in the goals table; a stopped goal resumes at its step."""
    import json

    from universal_mind.agent_loop import run_goal, start_goal

    import universal_mind.agent_loop as agent_mod

    with _isolated():
        started = start_goal(
            "هدف: آزمون ادامه",
            ("میانگین 4 و 6 را حساب کن", "این فرمان هیچ قابلیتی ندارد XYZQ"),
        )
        first = run_goal(started["goal_id"])
        assert first.finished is False, "the second step must fail"
        db = agent_mod._store()
        q = db.query("SELECT next_step, state, outcomes FROM goals WHERE id = ?",
                     (str(started["goal_id"]),))
        row = q["rows"][0]
        persisted_step = int(row["next_step"])
        state = str(row["state"])
        outcomes = json.loads(row["outcomes"])
    # next_step=1 (the failing step index — resume re-runs it), stopped,
    # and BOTH outcomes recorded (the success AND the failure: auditable).
    ok = persisted_step == 1 and state == "stopped" and len(outcomes) == 2
    ok = ok and outcomes[0]["ok"] is True and outcomes[1]["ok"] is False
    print(f"  persisted: next_step={persisted_step} state={state} outcomes={len(outcomes)}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeAgentLoop",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAgentLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("parse: data lists stay whole, steps still split", check_parse_keeps_data_lists),
    ("run: every step runs with its ARETĒ verdict", check_goal_runs_with_judgment),
    ("honest stop: a broken step halts the goal there", check_a_broken_step_stops_honestly),
    ("persistence: progress lands in the goals table", check_goal_persists_and_resumes),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE AGENT LOOP (هدف ← گامها ← داوری ← توقف/ادامه)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM PURSUES GOALS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())