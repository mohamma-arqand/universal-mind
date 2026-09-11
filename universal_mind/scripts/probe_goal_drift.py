#!/usr/bin/env python3
"""Probe: goal-drift detection — notice when the path has left the original goal.

A mind that keeps executing without checking whether it is still doing what it
set out to do is the classic over-eager agent. This probe proves the drift
detector: an on-course outcome is not flagged, a wrong-outcome (recipe instead of
a report) is flagged as drift, and an empty outcome is drift by definition. Exit
non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.goal_drift import assess_goal_drift


def check_on_course_is_not_drift() -> bool:
    result = assess_goal_drift("summarize the quarterly report", "here is the quarterly report summary")
    ok = result.drift is False and result.overlap > 0.0
    print(f"  on-course outcome is not flagged: {ok}")
    return ok


def check_wrong_outcome_is_drift() -> bool:
    result = assess_goal_drift("summarize the quarterly report", "here is a recipe for chocolate cake")
    ok = result.drift is True and "drifted" in result.reason
    print(f"  a wrong outcome is flagged as drift: {ok}")
    return ok


def check_empty_outcome_is_drift() -> bool:
    result = assess_goal_drift("summarize the report", "")
    ok = result.drift is True
    print(f"  an empty outcome is drift by definition: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeGoalDrift",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeGoalDrift", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("On-course outcome is not drift", check_on_course_is_not_drift),
    ("Wrong outcome is flagged as drift", check_wrong_outcome_is_drift),
    ("Empty outcome is drift", check_empty_outcome_is_drift),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Goal-drift detection probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: GOAL-DRIFT DETECTION (has the path left the goal?)")
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

    print("\nALL CHECKS PASSED - THE MIND CATCHES ITS OWN DRIFT" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())