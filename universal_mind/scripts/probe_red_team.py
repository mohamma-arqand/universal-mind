#!/usr/bin/env python3
"""Probe: red-team/blue-team — adversarial self-test.

A system that is never attacked does not know whether its defenses hold. This
probe proves the guard: a battery of hostile inputs (injection, secret, command,
hijack, exfiltrate) is blocked by the GuardedMouth defense (zero penetration),
while the unguarded mouth is penetrated — proving the defense has real value.
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

from universal_mind.arete.red_team import run_red_team
from universal_mind.mouth.commit import InMemoryMouth


def check_guarded_defense_blocks_all() -> bool:
    report = run_red_team()
    ok = report.penetrated == 0 and report.passed is True
    print(f"  GuardedMouth blocks all {len(report.attempts)} attacks: {ok}")
    return ok


def check_unguarded_is_penetrated() -> bool:
    report = run_red_team(InMemoryMouth())
    ok = report.penetrated > 0 and report.passed is False
    print(f"  unguarded mouth is penetrated (defense has value): {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeRedTeam",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeRedTeam", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Guarded defense blocks all attacks", check_guarded_defense_blocks_all),
    ("Unguarded mouth is penetrated", check_unguarded_is_penetrated),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Red-team/blue-team probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: RED-TEAM/BLUE-TEAM (adversarial self-test)")
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

    print("\nALL CHECKS PASSED - THE MIND TESTS ITS OWN DEFENSES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())