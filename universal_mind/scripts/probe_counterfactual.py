#!/usr/bin/env python3
"""Probe: counterfactual reasoning — does the judgment survive a reversed premise?

A verdict that only answers "which is best?" can be right by luck. This probe
proves the mind now asks the deeper question — "would this still hold if the
premise were false?" — and that a decision which collapses under a reversed
assumption is flagged *fragile*, while a no-winner verdict is reported honestly.
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

from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
from universal_mind.arete.counterfactual import counterfactual_check
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"out-{strategy_id}",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}},
    )


def check_fragile_decision_is_detected() -> bool:
    dispute = Dispute(goal="pick", candidates=[_candidate("good", 0.9), _candidate("bad", 0.3)])
    arbiter = InMemoryArbiter()
    verdict = arbiter.arbitrate(dispute)
    result = counterfactual_check(dispute, verdict, assumption="wisdom", arbiter=arbiter)
    ok = result.robust is False and "fragile" in result.explanation
    print(f"  a wisdom-hinged decision is flagged fragile: {ok}")
    return ok


def check_no_winner_is_reported_honestly() -> bool:
    dispute = Dispute(goal="pick", candidates=[_candidate("a", 0.5), _candidate("b", 0.5)])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = counterfactual_check(dispute, verdict)
    ok = result.original_winner is None and result.robust is False
    print(f"  a no-winner verdict is reported as non-robust: {ok}")
    return ok


def check_reversed_value_is_flipped() -> bool:
    import math

    dispute = Dispute(goal="pick", candidates=[_candidate("x", 0.8)])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = counterfactual_check(dispute, verdict, assumption="wisdom")
    ok = result.original_value == 0.8 and math.isclose(result.reversed_value, 0.2)
    print(f"  the reversed premise flips the value deterministically: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeCounterfactual",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeCounterfactual", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Fragile decision is detected", check_fragile_decision_is_detected),
    ("No-winner verdict is reported honestly", check_no_winner_is_reported_honestly),
    ("Reversed premise flips deterministically", check_reversed_value_is_flipped),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Counterfactual reasoning probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: COUNTERFACTUAL REASONING (does the judgment survive a reversed premise?)")
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

    print("\nALL CHECKS PASSED - THE MIND QUESTIONS ITS OWN PREMISES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())