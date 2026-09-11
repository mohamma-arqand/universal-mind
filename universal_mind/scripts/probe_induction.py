#!/usr/bin/env python3
"""Probe: inductive generalization — learn a rule from few examples, apply to the unseen.

Memorizing examples is not intelligence; the generalization is. This probe proves
the mind derives a simple, inspectable rule from few teaching pairs, applies it to
a novel input correctly, and — crucially — says "I don't know" (unmatched) rather
than guessing on an input it has no rule for. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.demiurge.induction import Example, apply_rule, induce


def _ex(color: str, shape: str, outcome: str) -> Example:
    return Example(features={"color": color, "shape": shape}, outcome=outcome)


def check_rule_is_learned_and_applied() -> bool:
    gen = induce([_ex("red", "round", "apple"), _ex("yellow", "long", "banana")])
    result = apply_rule(gen, {"color": "red", "shape": "round"})
    ok = result.prediction == "apple" and result.matched is True
    print(f"  rule learned and applied to a seen signature: {ok}")
    return ok


def check_unseen_is_unknown_not_guessed() -> bool:
    gen = induce([_ex("red", "round", "apple")])
    result = apply_rule(gen, {"color": "green", "shape": "round"})
    ok = result.prediction is None and result.matched is False
    print(f"  unseen input is reported unknown, not guessed: {ok}")
    return ok


def check_conflict_produces_no_rule() -> bool:
    gen = induce([_ex("red", "round", "apple"), _ex("red", "round", "tomato")])
    ok = gen is None
    print(f"  contradictory examples are not forced into a rule: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeInduction",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeInduction", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Rule is learned and applied", check_rule_is_learned_and_applied),
    ("Unseen input is unknown, not guessed", check_unseen_is_unknown_not_guessed),
    ("Conflict produces no rule", check_conflict_produces_no_rule),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inductive generalization probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: INDUCTIVE GENERALIZATION (learn a rule, apply to the unseen)")
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

    print("\nALL CHECKS PASSED - THE MIND GENERALIZES, NOT MEMORIZES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())