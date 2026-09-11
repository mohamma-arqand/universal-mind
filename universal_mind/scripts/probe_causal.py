#!/usr/bin/env python3
"""Probe: causal reasoning — beyond correlation, toward "why".

Observing two events co-occur is not enough to know one causes the other. This
probe proves the mind separates *necessary* causes (the effect never happens
without them) from *incidental* ones (they co-occur but do not drive the effect),
via the intervention question "if the cause were removed, would the effect still
happen?". Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.demiurge.causal import TraceEvent, infer_causes


def _e(event_id: str, cause: str, effect: bool) -> TraceEvent:
    return TraceEvent(event_id=event_id, cause=cause, effect=effect)


def check_necessary_cause_is_found() -> bool:
    events = [_e("1", "A", True), _e("2", "A", True), _e("3", "B", False), _e("4", "B", False)]
    findings = {f.cause: f for f in infer_causes(events)}
    ok = findings["A"].necessary is True and findings["B"].necessary is False
    print(f"  necessary cause separated from incidental: {ok}")
    return ok


def check_incidental_cause_is_flagged() -> bool:
    events = [_e("1", "C", True), _e("2", "D", True), _e("3", "D", True)]
    findings = {f.cause: f for f in infer_causes(events)}
    ok = findings["C"].necessary is False and "incidental" in findings["C"].explanation
    print(f"  incidental cause explained (co-occurs, does not drive): {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeCausalReasoning",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeCausalReasoning", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Necessary cause separated from incidental", check_necessary_cause_is_found),
    ("Incidental cause is explained", check_incidental_cause_is_flagged),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Causal reasoning probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: CAUSAL REASONING (separate necessary from incidental)")
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

    print("\nALL CHECKS PASSED - THE MIND ASKS WHY, NOT JUST WHAT" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())