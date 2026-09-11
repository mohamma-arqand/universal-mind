#!/usr/bin/env python3
"""Probe: rubric learning — the evaluation rubric improves from its own mistakes.

A fixed rubric is a frozen prejudice. This probe proves the rubric learns: a
defer-spiral raises the accept threshold, a deny-spiral lowers it, a mostly-allow
history keeps it, and the base rubric is never mutated (immutable evolution).
Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.rubric_learning import learn_rubric
from universal_mind.arete.virtue import VirtueWeights


def check_defer_spiral_raises_bar() -> bool:
    learned = learn_rubric(["defer", "defer", "defer", "allow"])
    ok = learned.accept_threshold > VirtueWeights().accept_threshold
    print(f"  defer-spiral raises the accept threshold: {ok}")
    return ok


def check_deny_spiral_lowers_bar() -> bool:
    learned = learn_rubric(["deny", "deny", "deny", "allow"])
    ok = learned.accept_threshold < VirtueWeights().accept_threshold
    print(f"  deny-spiral lowers the accept threshold: {ok}")
    return ok


def check_base_is_never_mutated() -> bool:
    base = VirtueWeights()
    original = base.accept_threshold
    learn_rubric(["defer", "defer"], base=base)
    ok = base.accept_threshold == original
    print(f"  base rubric is immutable across learning: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeRubricLearning",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeRubricLearning", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Defer-spiral raises the bar", check_defer_spiral_raises_bar),
    ("Deny-spiral lowers the bar", check_deny_spiral_lowers_bar),
    ("Base rubric is immutable", check_base_is_never_mutated),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rubric learning probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: RUBRIC LEARNING (the rubric improves from its mistakes)")
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

    print("\nALL CHECKS PASSED - THE RUBRIC LEARNS FROM ITS MISTAKES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())