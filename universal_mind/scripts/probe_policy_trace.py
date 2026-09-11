#!/usr/bin/env python3
"""Probe: provable policy — every allow/deny as a verifiable reason chain.

A decision described only by a sentence must be trusted, not checked. This probe
proves the provability layer: an arbitration verdict becomes a structured chain
of reason steps, each independently verifiable (measurement / hard-gate / winner
/ no-winner), so "why did you allow or deny?" is replayable step-by-step. Exit
non-zero unless all hold.
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
from universal_mind.arete.policy_trace import trace_verdict
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id, output="out",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}},
    )


def check_allow_has_verifiable_chain() -> bool:
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[_candidate("x", 0.9)]))
    trace = trace_verdict(verdict)
    checks = {s.check for s in trace.steps}
    ok = trace.decision == "allow" and "winner" in checks and "measurement" in checks
    print(f"  allow decision decomposes into a verifiable chain: {ok}")
    return ok


def check_deny_records_no_winner() -> bool:
    c = CandidateOutput(strategy_id="weak", output="out", metadata={
        "virtues": {"justice": 0.1, "wisdom": 0.1, "courage": 0.1, "temperance": 0.1}})
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[c]))
    trace = trace_verdict(verdict)
    ok = trace.decision == "deny" and any(s.check == "no_winner" for s in trace.steps)
    print(f"  deny decision records a no-winner step: {ok}")
    return ok


def check_disqualification_is_traced() -> bool:
    c = CandidateOutput(strategy_id="bad", output="out", metadata={
        "virtues": {"justice": 0.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}})
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[c]))
    trace = trace_verdict(verdict)
    ok = any(s.check == "hard_gate" and s.passed is False for s in trace.steps)
    print(f"  a disqualifying hard-gate is traced: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeProvablePolicy",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeProvablePolicy", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Allow decomposes into a verifiable chain", check_allow_has_verifiable_chain),
    ("Deny records a no-winner step", check_deny_records_no_winner),
    ("Disqualification is traced", check_disqualification_is_traced),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Provable policy probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: PROVABLE POLICY (every decision as a verifiable reason chain)")
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

    print("\nALL CHECKS PASSED - EVERY DECISION IS A REPLAYABLE TRACE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())