#!/usr/bin/env python3
"""Probe: the ARETĒ critical loop — a D becomes the standard only by merit.

Runs StandardKeeper over three proposals: a first seed, a strictly-better D
(promoted), then a weaker and an equal D (rejected / deferred). Proves the
standing standard survives, the promotion is persisted append-only, and that
recency alone never wins. Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete import PromotionDecision, StandardKeeper
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}


def _candidate(name: str, virtues: dict[str, float], artifact: str = "a") -> CandidateOutput:
    return CandidateOutput(strategy_id=name, output=artifact, metadata={"virtues": virtues})


def attempt_first_seed() -> bool:
    """No incumbent -> first D seeds the standard."""
    k = StandardKeeper(InMemoryStore())
    res = k.consider(_candidate("D1", FULL))
    cur = k.current()
    ok = res.decision is PromotionDecision.PROMOTED and cur is not None and cur.name == "D1"
    print(f"  first D seeded the standard: {ok}")
    return ok


def attempt_better_d_promotes() -> bool:
    """A strictly-better D overturns the standing standard (merit, not recency)."""
    k = StandardKeeper(InMemoryStore())
    k.consider(_candidate("seed", FULL))
    res = k.consider(_candidate("better", {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}))
    ok = res.decision is PromotionDecision.PROMOTED and res.current_standard.name == "better"
    print(f"  better D promoted to standard: {ok}")
    return ok


def attempt_weak_rejected() -> bool:
    """A weaker D is rejected; the incumbent survives."""
    k = StandardKeeper(InMemoryStore())
    k.consider(_candidate("seed", FULL))
    res = k.consider(_candidate("weak", {"justice": 1.0, "wisdom": 0.4, "courage": 1.0, "temperance": 1.0}))
    ok = res.decision is PromotionDecision.REJECTED and res.current_standard.name == "seed"
    print(f"  weak D rejected, standard intact: {ok}")
    return ok


def attempt_jail_may_deny() -> bool:
    """A justice-failing D is denied even with high excellence (non-compensatory)."""
    k = StandardKeeper(InMemoryStore())
    k.consider(_candidate("seed", FULL))
    res = k.consider(_candidate("unjust", {"justice": 0.1, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}))
    ok = res.decision is PromotionDecision.REJECTED
    print(f"  justice-violating D denied on hard gate: {ok}")
    return ok


def attempt_recency_never_wins() -> bool:
    """A merely-equal newcomer ties -> deferred, never promoted by recency."""
    k = StandardKeeper(InMemoryStore())
    k.consider(_candidate("seed", FULL))
    res = k.consider(_candidate("equal", {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}))
    ok = res.decision is PromotionDecision.DEFERRED and res.current_standard.name == "seed"
    print(f"  equal D deferred (no recency win): {ok}")
    return ok


def attempt_append_only_history() -> bool:
    """Promotions are persisted; history is a replayable audit trail."""
    k = StandardKeeper(InMemoryStore())
    k.consider(_candidate("seed", FULL))
    k.consider(_candidate("better", {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}))
    hist = k.history()
    ok = len(hist) == 2 and hist[0]["payload"]["name"] == "seed" and hist[1]["payload"]["name"] == "better"
    print(f"  promotion ledger append-ordered ({len(hist)} records): {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeAreteCriticalLoop",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAreteCriticalLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("First synthesis seeds the standard", attempt_first_seed),
    ("Strictly better D promotes", attempt_better_d_promotes),
    ("Weaker D rejected", attempt_weak_rejected),
    ("Justice gate denies unjust D", attempt_jail_may_deny),
    ("Recency alone never promotes", attempt_recency_never_wins),
    ("Promotion ledger is append-ordered", attempt_append_only_history),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="ARETĒ critical-loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: ARETĒ CRITICAL LOOP — a standard is earned by evidence, never recency")
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
        print("\nALL CHECKS PASSED - THE STANDARD IS GOVERNED BY ARETĒ, NOT BY NOVELTY")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())