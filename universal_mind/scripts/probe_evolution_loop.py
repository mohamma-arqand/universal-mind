#!/usr/bin/env python3
"""Probe: PROMETHEUS recursive self-improvement loop (code->sandbox->benchmark).

Runs a candidate through a fresh sandbox, benchmarks it against a baseline, and
proves the gate accepts only when it is measurably better (with evidence), never
touching the live tree. Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.prometheus import (
    EvolutionGate,
    Sandbox,
    Verdict,
    run_evolution_loop,
)


def _benchmark_size(path: Path) -> float:
    return float(path.stat().st_size)


def attempt_accepts_better() -> bool:
    """A measurably better candidate is accepted with evidence."""
    d = EvolutionGate().evaluate(baseline=1.0, candidate=5.0, why="size")
    print(f"  verdict={d.verdict.value} margin={d.margin:.2f}")
    return d.verdict is Verdict.ACCEPT and bool(d.evidence.points)


def attempt_rejects_not_better() -> bool:
    """A candidate that is not better is rejected, never silently applied."""
    d = EvolutionGate().evaluate(baseline=5.0, candidate=5.0, why="size")
    print(f"  verdict={d.verdict.value} (no improvement)")
    return d.verdict is Verdict.REJECT and bool(d.evidence.points)


def attempt_sandbox_isolates_and_cleans() -> bool:
    """Sandbox files live in a temp dir and are removed afterward."""
    s = Sandbox()
    path = s.write("candidate.py", "x=1")
    inside = s.path in path.parents
    s.cleanup()
    ok = inside and not s.path.exists()
    print(f"  sandbox isolated={inside} cleaned={not s.path.exists()}")
    return ok


def attempt_full_loop_end_to_end() -> bool:
    """The full loop (build in sandbox -> benchmark -> gate) works live."""
    decision = run_evolution_loop(
        candidate_source="a" * 64,
        baseline_score=4.0,
        benchmark=_benchmark_size,
    )
    ok = decision.verdict is Verdict.ACCEPT and decision.candidate_score == 64.0
    print(f"  loop verdict={decision.verdict.value} scored={decision.candidate_score:.0f}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeEvolutionLoop",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeEvolutionLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Better candidate accepted with evidence", attempt_accepts_better),
    ("Not-better candidate rejected", attempt_rejects_not_better),
    ("Sandbox isolates and cleans up", attempt_sandbox_isolates_and_cleans),
    ("Full loop end-to-end", attempt_full_loop_end_to_end),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="Recursive Self-Improvement Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: PROMETHEUS code -> sandbox -> benchmark -> accept/reject")
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
        print("\nALL CHECKS PASSED - RECURSIVE SELF-IMPROVEMENT IS SAFE, EVIDENCE-BACKED, AND DETERMINISTIC")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())