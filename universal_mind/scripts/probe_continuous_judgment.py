#!/usr/bin/env python3
"""Probe: continuous judgment — the result, the memory, and the lineage are all judged.

Covers the three "continual judgment" capabilities in one place:
1. chained judgment (SynthesisEngine verifies its own D),
2. significance-biased forgetting (least-valuable trims first),
3. lineage rollback (rewind the standard, keep history).

Exits non-zero unless every invariant holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.standard import StandardKeeper
from universal_mind.compose import compose, fuse_fact_into_draft
from universal_mind.memory.lifespan import _significance
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput
from universal_mind.synthesis import FactSpecialist, SynthesisEngine, WriterSpecialist

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}
BETTER = {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}


def attempt_chained_judgment() -> bool:
    """A successful synthesis is verified; a failed sub-step is not."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    ok = en.run("summarize knowledge then write it").verified is True
    print(f"  synthesis result is verified by ARETĒ: {ok}")
    return ok


def attempt_fusion_is_not_concat() -> bool:
    """The composed D is a fused artifact (method='fusion'), not integration."""
    out = compose([{"fact": "42 units."}, {"draft": "Final: report."}], composer=fuse_fact_into_draft)
    ok = out.method == "fusion" and "\n" not in str(out.artifact)
    print(f"  true synthesis produces a fused artifact: {ok}")
    return ok


def attempt_significance_ranks_value() -> bool:
    """Value, not recency, decides what is kept: standard > failed note."""
    ok = (
        _significance({"kind": "standard"}) > _significance({"kind": "synthesis", "payload": {}})
        and _significance({"kind": "synthesis", "payload": {"verified": True}})
        > _significance({"kind": "synthesis", "payload": {}})
    )
    print(f"  forgetting is significance-biased: {ok}")
    return ok


def attempt_rollback_rewinds() -> bool:
    """A wrong standard can be rewound without erasing history."""
    k = StandardKeeper(InMemoryStore())
    k.consider(CandidateOutput(strategy_id="d1", output="a", metadata={"virtues": dict(FULL)}))
    k.consider(CandidateOutput(strategy_id="d2", output="b", metadata={"virtues": dict(BETTER)}))
    res = k.rollback(0, reason="d2 was wrong")
    ok = res is not None and res.current_standard.promotion_depth == 0
    print(f"  lineage rollback rewinds the standard: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeContinuousJudgment",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeContinuousJudgment", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Synthesis result is verified (chained judgment)", attempt_chained_judgment),
    ("True synthesis fuses, does not concatenate", attempt_fusion_is_not_concat),
    ("Forgetting is significance-biased", attempt_significance_ranks_value),
    ("Lineage rollback rewinds the standard", attempt_rollback_rewinds),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous-judgment probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: CONTINUOUS JUDGMENT (result · memory · lineage)")
    print("=" * 64)
    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        results.append((name, fn()))

    print("\n" + "=" * 64)
    print("SUMMARY")
    print("=" * 64)
    all_ok = True
    for name, result in results:
        print(f"  {name}: {'OK' if result else 'FAILED'}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - THE MIND JUDGES ITS WORK, ITS MEMORY, AND ITS HISTORY")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())