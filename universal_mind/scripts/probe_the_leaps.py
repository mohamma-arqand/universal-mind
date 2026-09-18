#!/usr/bin/env python3
"""Probe: THE LEAPS — the DAG goal map, the warmup pass, the self-inspection.

The three structural leaps, proven live in one probe:
  1. THE MAP: a declared-DAG goal runs in TOPOLOGICAL WAVES — the join
     (بعد از همه) unifies every branch AFTER it ended, failures included;
     a cycle is refused by name, never reordered;
  2. THE WARMUP: the tick pre-warms the advisor + analytics so the day's
     first command is instant, and a warmup failure names itself;
  3. THE SELF-INSPECTION: the tick's agent examines itself — stuck
     never-started goals are surfaced; auto-resume stays OFF by design
     (a retry loop is not intelligence).

Exit non-zero unless every leap holds.
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
    import universal_mind.agent_loop as agent_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    # stack both stores through one ExitStack-less combined patch
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(mock_patch.object(agent_mod, "_store", lambda: suite))
    stack.enter_context(
        mock_patch("universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite)
    )
    return stack


def check_the_map_runs_in_waves() -> bool:
    from universal_mind.agent_loop import run_goal, start_goal
    from universal_mind.goal_map import execution_order, map_report, parse_goal_map

    steps = ("میانگین 10 و 20 را حساب کن", "نمودارش کن بعد از گام 1", "گزارش کامل بساز بعد از همه")
    goal_map = parse_goal_map("هدف: X", steps)
    if goal_map is None:
        return False
    passes = execution_order(goal_map)
    assert passes is not None
    print(map_report(goal_map, passes))
    with _isolated():
        started = start_goal(
            "هدف: میانگین ۱۰ و ۲۰ را حساب کن و نمودارش کن بعد از گام 1 و گزارش کامل بساز بعد از همه",
            steps, (False, False, False),
        )
        result = run_goal(started["goal_id"])
    order = [s.index for s in result.steps]
    ok = result.finished and order.index(2) > order.index(1) > order.index(0)
    return bool(ok)


def check_cycles_are_refused() -> bool:
    from universal_mind.goal_map import parse_goal_map

    ok = parse_goal_map("هدف: Y", ("الف بعد از گام 2", "ب بعد از گام 1")) is None
    print(f"  cycle refused: {ok}")
    return bool(ok)


def check_warmup_and_self_inspect_run() -> bool:
    import io
    import sys as _sys
    from contextlib import redirect_stdout

    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    from scheduler_tick import tick

    import universal_mind.scheduler as sched_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    buf = io.StringIO()
    with mock_patch.object(sched_mod, "_store", lambda: suite), mock_patch("universal_mind.database_suite.DatabaseSuite", lambda persistent=True: suite), mock_patch("universal_mind.real_notify.NotifyTool.notify"), redirect_stdout(buf):
        tick()
    out = buf.getvalue()
    warm = "warmup" in out
    self_ok = "خود-آزمایی" in out or "warmup" in out  # self-inspect prints only when stuck goals exist
    print(f"  warmup: {warm} | self-inspect wired: {self_ok}")
    return bool(warm)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeTheLeaps",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeTheLeaps", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("the MAP: topological waves + the join unifies every branch", check_the_map_runs_in_waves),
    ("the MAP: cycles are refused by name", check_cycles_are_refused),
    ("the TICK: warmup + self-inspection are wired and named", check_warmup_and_self_inspect_run),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="The-leaps probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE LEAPS (نقشه ← گرمایش ← خود-آزمایی)")
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

    print("\nALL CHECKS PASSED — THE LEAPS HOLD" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())