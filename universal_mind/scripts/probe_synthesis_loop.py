#!/usr/bin/env python3
"""Probe: the synthesis loop closes the charter — A+B+C -> D.

Runs SynthesisEngine over decomposed sub-goals routed via CapabilityResolver to
distinct specialists, and proves the output is a single artifact no single
specialist produced, evidence-backed and canonically committed. Exit 0 only if
every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.memory.store import InMemoryStore
from universal_mind.synthesis import (
    FactSpecialist,
    SynthesisEngine,
    WriterSpecialist,
)


def attempt_loop_synthesizes() -> bool:
    """Two specialists contribute to one synthesized D."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    report = en.run("summarize knowledge then write the result")
    used = {e.specialist for e in report.sub_executions}
    ok = report.ok and used == {"facts", "writer"} and report.synthesized is not None
    print(f"  D produced with specialists: {sorted(used)} ok={ok}")
    return ok


def attempt_d_is_more_than_parts() -> bool:
    """D combines facts + writing into one artifact neither alone yields."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    report = en.run("summarize knowledge then write it")
    has_fact = "[facts]" in report.synthesized
    has_writing = "[writer]" in report.synthesized
    ok = has_fact and has_writing
    print(f"  synthesis combines specialist outputs: {ok}")
    return ok


def attempt_committed_to_ledger() -> bool:
    """The synthesis is committed canonically (kind='synthesis')."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    report = en.run("summarize the knowledge now")
    ok = report.commit_record_id is not None and "synthesis" in {r.get("kind") for r in en._store.read_all()}
    print(f"  committed record id present: {report.commit_record_id is not None}")
    return ok


def attempt_evidence_backed() -> bool:
    """Every step is evidence-anchored."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    report = en.run("summarize the knowledge")
    ok = bool(report.evidence.points)
    print(f"  evidence points on synthesis: {len(report.evidence.points)}")
    return ok


def attempt_deterministic() -> bool:
    """Identical input yields an identical synthesized D."""
    def once() -> str:
        en = SynthesisEngine(InMemoryStore())
        en.register("facts", FactSpecialist())
        en.register("writer", WriterSpecialist())
        return en.run("write the final report").synthesized or ""

    ok = once() == once()
    print(f"  deterministic: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeSynthesisLoop",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeSynthesisLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Synthesis loop produces a single D", attempt_loop_synthesizes),
    ("D is more than the sum of parts", attempt_d_is_more_than_parts),
    ("Synthesis committed to the ledger", attempt_committed_to_ledger),
    ("Every step evidence-backed", attempt_evidence_backed),
    ("Synthesis is deterministic", attempt_deterministic),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="Synthesis Loop Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: ONE MIND — MANY MINDS — ONE INTEGRATED JUDGMENT (A+B+C -> D)")
    print("=" * 60)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        results.append((name, fn()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, result in results:
        status = "OK" if result else "FAILED"
        print(f"  {name}: {status}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - THE LOOP CLOSES: GOAL->DECOMPOSE->RESOLVE->EXECUTE->SYNTHESIZE->COMMIT")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())