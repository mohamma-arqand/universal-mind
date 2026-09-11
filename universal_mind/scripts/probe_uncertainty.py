#!/usr/bin/env python3
"""Probe: epistemic uncertainty — know what you do not know, and say so.

A judge that must always pick will pick wrong on thin evidence. This probe proves
the mind has a first-class "I don't know": insufficient evidence yields UNKNOWN
with a reason, a single genuine counter-evidence yields CONFLICTED even against
strong support, and sufficient evidence yields KNOWN. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.uncertainty import (
    EpistemicStatus,
    assess_uncertainty,
    assess_verdict_uncertainty,
)


def check_thin_evidence_is_unknown() -> bool:
    result = assess_uncertainty(0.2)
    ok = result.status is EpistemicStatus.UNKNOWN and "not enough" in result.reason
    print(f"  thin evidence is honestly UNKNOWN: {ok}")
    return ok


def check_conflict_overrides_strong_evidence() -> bool:
    result = assess_uncertainty(0.9, conflicts=1)
    ok = result.status is EpistemicStatus.CONFLICTED
    print(f"  counter-evidence overrides strong support: {ok}")
    return ok


def check_verdict_uncertainty_ties_to_evidence() -> bool:
    from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
    from universal_mind.powers.judgment import CandidateOutput

    dispute = Dispute(goal="pick", candidates=[
        CandidateOutput(strategy_id="x", output="out", metadata={
            "virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}})
    ])
    verdict = InMemoryArbiter().arbitrate(dispute)
    result = assess_verdict_uncertainty(verdict)
    ok = result.status is EpistemicStatus.KNOWN and result.evidence_weight > 0
    print(f"  verdict uncertainty is tied to its own evidence weight: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeEpistemicUncertainty",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeEpistemicUncertainty", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Thin evidence is honestly UNKNOWN", check_thin_evidence_is_unknown),
    ("Counter-evidence overrides strong support", check_conflict_overrides_strong_evidence),
    ("Verdict uncertainty ties to its evidence", check_verdict_uncertainty_ties_to_evidence),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Epistemic uncertainty probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: EPISTEMIC UNCERTAINTY (know what you do not know)")
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

    print("\nALL CHECKS PASSED - THE MIND KNOWS WHEN IT DOES NOT KNOW" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())