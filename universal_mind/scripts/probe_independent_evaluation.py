#!/usr/bin/env python3
"""Probe: independent evaluation — a second judge outside the loop.

A self-aware mind that only self-assesses has one blind spot: it never meets a
foreign standard. This probe proves the independent evaluator exists and works:
it scores the loop against an external rubric (not the loop's own signals),
fails a fresh loop on the lineage-evidence dimension, and — crucially — writes
an ``external_audit`` ledger entry so the second judge is as auditable as the
first. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.external_evaluator import evaluate_loop
from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput


def _loop_with_judgments() -> tuple[InMemoryStore, SelfAwarenessLoop]:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    loop.consider(CandidateOutput(strategy_id="a", output="x", metadata={
        "virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}}))
    return store, loop


def check_second_judge_passes_healthy_loop() -> bool:
    _, loop = _loop_with_judgments()
    result = evaluate_loop(loop)
    ok = result.passed is True and result.score == 1.0
    print(f"  external rubric passes a healthy loop: {ok}")
    return ok


def check_fresh_loop_fails_evidence() -> bool:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    result = evaluate_loop(loop)
    lineage = next(f for f in result.findings if f.dimension == "lineage_has_evidence")
    ok = lineage.ok is False and result.passed is False
    print(f"  fresh (unjudged) loop is flagged for lack of evidence: {ok}")
    return ok


def check_audit_is_recorded_in_ledger() -> bool:
    store, loop = _loop_with_judgments()
    result = evaluate_loop(loop, store=store)
    kinds = [r.get("kind") for r in store.read_all()]
    ok = result.ledger_record_id is not None and "external_audit" in kinds
    print(f"  external_audit entry is written to the ledger: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeIndependentEvaluation",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeIndependentEvaluation", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("External rubric passes a healthy loop", check_second_judge_passes_healthy_loop),
    ("Fresh loop is flagged for lack of evidence", check_fresh_loop_fails_evidence),
    ("external_audit is recorded in the ledger", check_audit_is_recorded_in_ledger),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent evaluation probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: INDEPENDENT EVALUATION (a second judge, outside the self-check loop)")
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
        print(f"  {name}: {'OK' if result else 'FAILED'}")

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    print("\nALL CHECKS PASSED - THE MIND HAS A SECOND JUDGE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())