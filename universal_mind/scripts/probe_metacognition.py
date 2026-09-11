#!/usr/bin/env python3
"""Probe: metacognition — the mind folds its own reasoning into one trust judgment.

The deepest cognitive move is reasoning about reasoning. This probe proves the
metacognitive layer: it folds three prior self-reasoning products (counterfactual
robustness, epistemic certainty, hypothesis ensemble convergence) into ONE reasoned
confidence band — and refuses to trust a fragile/thin decision. Exit non-zero
unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.counterfactual import CounterfactualResult
from universal_mind.arete.uncertainty import EpistemicStatus
from universal_mind.core.metacognition import MetaConfidence, assess_metacognition
from universal_mind.demiurge.hypotheses import EnsembleResult, Hypothesis


def _robust(robust: bool) -> CounterfactualResult:
    return CounterfactualResult(
        original_winner="x", robust=robust, counterfactual_winner="x",
        explanation="e", reversed_dimension="wisdom", original_value=0.9, reversed_value=0.1,
    )


def _ensemble(converged: bool) -> EnsembleResult:
    h = Hypothesis("a", "r", 0.9, 0.9)
    return EnsembleResult((h,), h, (), converged)


def check_all_pass_is_high() -> bool:
    v = assess_metacognition(_robust(True), EpistemicStatus.KNOWN, _ensemble(True))
    ok = v.confidence is MetaConfidence.HIGH
    print(f"  all self-checks pass -> HIGH confidence: {ok}")
    return ok


def check_fragile_is_skeptical() -> bool:
    v = assess_metacognition(_robust(False), EpistemicStatus.UNKNOWN, _ensemble(False))
    ok = v.confidence is MetaConfidence.SKEPTICAL
    print(f"  a fragile + unknown + unconverged decision is distrusted: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeMetacognition",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeMetacognition", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("All self-checks pass -> HIGH", check_all_pass_is_high),
    ("Fragile decision is distrusted", check_fragile_is_skeptical),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Metacognition probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: METACOGNITION (reasoning about its own reasoning)")
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

    print("\nALL CHECKS PASSED - THE MIND JUDGES ITS OWN JUDGING" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())