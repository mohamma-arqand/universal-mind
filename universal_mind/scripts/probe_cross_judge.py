#!/usr/bin/env python3
"""Probe: cross-model judging — a second foreign judge adjudicates the first.

An arbiter that always agrees with itself can drift unnoticed. This probe proves
two independently-tuned rubrics are compared: agreement yields high confidence,
and a foreign rubric (justice + courage hard gate) genuinely diverges from the
primary (justice-only) on a low-courage candidate — so alignment is real, not an
echo. Exit non-zero unless all hold.
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
from universal_mind.arete.cross_judge import cross_judge
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float, courage: float = 1.0) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"out-{strategy_id}",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": courage, "temperance": 1.0}},
    )


def check_agreement_yields_high_confidence() -> bool:
    dispute = Dispute(goal="pick", candidates=[_candidate("good", 0.95), _candidate("bad", 0.2)])
    primary = InMemoryArbiter().arbitrate(dispute)
    result = cross_judge(dispute, primary)
    ok = result.aligned is True and result.confidence == 1.0
    print(f"  two rubrics agree on a clear winner: {ok}")
    return ok


def check_foreign_rubric_diverges_on_courage() -> bool:
    dispute = Dispute(goal="pick", candidates=[_candidate("coward", 0.8, courage=0.1)])
    primary = InMemoryArbiter().arbitrate(dispute)
    result = cross_judge(dispute, primary)
    ok = result.aligned is False and "diverge" in result.explanation
    print(f"  foreign courage-gate diverges from the primary: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeCrossJudge",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeCrossJudge", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Agreement yields high confidence", check_agreement_yields_high_confidence),
    ("Foreign rubric diverges on courage", check_foreign_rubric_diverges_on_courage),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-judge probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: CROSS-MODEL JUDGING (two independent rubrics compared)")
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

    print("\nALL CHECKS PASSED - THE MIND IS JUDGED BY A FOREIGN JUDGE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())