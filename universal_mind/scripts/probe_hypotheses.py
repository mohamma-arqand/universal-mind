#!/usr/bin/env python3
"""Probe: hypothesis ensemble — several readings, converge on evidence.

A mind that locks into its first reading is exactly the "expensively wrong"
failure the charter warns about. This probe proves the ensemble holds several
parallel readings at once, ranks them by evidence, keeps the runners-up live,
and reports honestly when the field has not yet converged. Exit non-zero unless
all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.demiurge.hypotheses import Hypothesis, HypothesisEnsemble


def _h(hypothesis_id: str, evidence: float, simplicity: float) -> Hypothesis:
    return Hypothesis(hypothesis_id=hypothesis_id, reading=hypothesis_id, evidence_weight=evidence, simplicity=simplicity)


def check_best_ranked_first_with_live_alternatives() -> bool:
    ensemble = HypothesisEnsemble(min_alternatives=2)
    result = ensemble.converge([_h("a", 0.9, 0.9), _h("b", 0.6, 0.9), _h("c", 0.5, 0.9)])
    assert result.best is not None
    ok = result.best.hypothesis_id == "a" and {x.hypothesis_id for x in result.alternatives} == {"b", "c"}
    print(f"  best ranked first, runners-up stay live: {ok}")
    return ok


def check_convergence_is_honest() -> bool:
    decisive = HypothesisEnsemble(margin=0.1).converge([_h("a", 0.9, 0.9), _h("b", 0.3, 0.9)])
    thin = HypothesisEnsemble(margin=0.1).converge([_h("a", 0.6, 0.5), _h("b", 0.55, 0.5)])
    ok = decisive.converged is True and thin.converged is False
    print(f"  decisive margin converges, thin margin stays open: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeHypothesisEnsemble",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeHypothesisEnsemble", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Best ranked first with live alternatives", check_best_ranked_first_with_live_alternatives),
    ("Convergence is honest", check_convergence_is_honest),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Hypothesis ensemble probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: HYPOTHESIS ENSEMBLE (several readings, converge on evidence)")
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

    print("\nALL CHECKS PASSED - THE MIND HOLDS SEVERAL MINDS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())