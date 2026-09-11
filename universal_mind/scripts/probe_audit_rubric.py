#!/usr/bin/env python3
"""Probe: external audit rubric — a fixed, neutral yardstick, not self-report.

The last proof of 'beyond world class' is an independent measure. This probe
proves the yardstick exists and is *honest*: a fixed, versioned rubric scores the
system from external measurements (an independent test run, probe run, type
check, adversarial sweep, robustness sample), gives a reasoned verdict, and does
NOT flatter a weak measurement. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.audit_rubric import ExternalRubric


def _clean() -> dict:
    return {"tests_failures": 0, "probes_failed": 0, "mypy_errors": 0, "red_team_penetrated": 0, "robust_fraction": 1.0}


def check_clean_measurements_score_high() -> bool:
    card = ExternalRubric().score(_clean())
    ok = card.score == 1.0 and "holds up" in card.verdict
    print(f"  clean external measurements score a high, honest verdict: {ok}")
    return ok


def check_weak_measurements_are_not_flattered() -> bool:
    weak = {"tests_failures": 15, "probes_failed": 5, "mypy_errors": 3, "red_team_penetrated": 4, "robust_fraction": 0.2}
    card = ExternalRubric().score(weak)
    ok = card.score < 0.5 and ("not yet auditable" in card.verdict or "incomplete" in card.verdict)
    print(f"  a weak system is honestly scored low, never flattered: {ok}")
    return ok


def check_rubric_is_versioned() -> bool:
    card = ExternalRubric(version="1.0.0").score(_clean())
    ok = card.rubric_version == "1.0.0"
    print(f"  the yardstick is versioned (auditable which rubric scored): {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeExternalRubric",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeExternalRubric", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Clean measurements score high honestly", check_clean_measurements_score_high),
    ("Weak measurements are not flattered", check_weak_measurements_are_not_flattered),
    ("Rubric is versioned", check_rubric_is_versioned),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="External audit rubric probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: EXTERNAL AUDIT RUBRIC (a neutral yardstick, not self-report)")
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

    print("\nALL CHECKS PASSED - THE YARDSTICK JUDGES WITHOUT FLATTERY" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())