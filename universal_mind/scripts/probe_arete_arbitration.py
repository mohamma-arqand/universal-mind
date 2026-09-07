#!/usr/bin/env python3
"""Probe: ARETĒ arbitration is deterministic and non-compensatory.

Confirms the arbitration rules hold from outside the test suite:
the best overall candidate is DISQUALIFIED if it fails a hard-gate virtue;
excellence ties are ruled DEFER, never guessed; weights change the winner;
and repeated arbitration is identical. Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete import (
    AreteError,
    CardinalVirtue,
    Dispute,
    InMemoryArbiter,
    VirtueWeights,
)
from universal_mind.powers.judgment import CandidateOutput, Verdict


def candid(strategy_id: str, virtues: dict[str, float]) -> CandidateOutput:
    """Build a candidate with a precomputed virtue observation."""
    return CandidateOutput(strategy_id=strategy_id, output="result", metadata={"virtues": virtues})


def perfect() -> dict[str, float]:
    """An observation that satisfies every gate."""
    return {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 1.0}


def attempt_non_compensatory() -> bool:
    """A flashy but unjust candidate must lose to a just one."""
    unjust = candid("flashy", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.1})
    just = candid("honest", {"wisdom": 0.5, "courage": 0.5, "temperance": 0.5, "justice": 0.9})
    verdict = InMemoryArbiter().arbitrate(Dispute("pick", [unjust, just]))
    disqualified = next(s for s in verdict.scorecards if s.candidate_strategy_id == "flashy")
    ok = verdict.winner_strategy_id == "honest" and disqualified.disqualified
    print(f"  Winner: {verdict.winner_strategy_id} | flashy disqualified: {disqualified.disqualified}")
    return ok


def attempt_tie_defers() -> bool:
    """An exact excellence tie is DEFER with no guessed winner."""
    verdict = InMemoryArbiter().arbitrate(
        Dispute("pick", [candid("a", perfect()), candid("b", perfect())])
    )
    ok = verdict.decision is Verdict.DEFER and verdict.winner_strategy_id is None
    print(f"  Decision: {verdict.decision.value} | winner: {verdict.winner_strategy_id}")
    return ok


def attempt_weights_change_winner() -> bool:
    """Weighting drives which candidate is the most excellent."""
    weights = VirtueWeights(
        weights={
            CardinalVirtue.WISDOM: 10.0,
            CardinalVirtue.COURAGE: 1.0,
            CardinalVirtue.TEMPERANCE: 1.0,
            CardinalVirtue.JUSTICE: 1.0,
        }
    )
    wise = candid("wise", {"wisdom": 0.9, "courage": 0.3, "temperance": 0.3, "justice": 0.9})
    strong = candid("strong", {"wisdom": 0.3, "courage": 0.9, "temperance": 0.9, "justice": 0.9})
    verdict = InMemoryArbiter(weights=weights).arbitrate(Dispute("pick", [strong, wise]))
    ok = verdict.winner_strategy_id == "wise"
    print(f"  Winner under wisdom-weighted rubric: {verdict.winner_strategy_id}")
    return ok


def attempt_deterministic() -> bool:
    """Identical disputes arbitrate identically."""
    cands = [
        candid("a", {"wisdom": 0.8, "courage": 0.6, "temperance": 0.7, "justice": 0.9}),
        candid("b", {"wisdom": 0.6, "courage": 0.8, "temperance": 0.8, "justice": 0.7}),
    ]
    arbiter = InMemoryArbiter()
    one = arbiter.arbitrate(Dispute("pick", cands))
    two = arbiter.arbitrate(Dispute("pick", cands))
    ok = one == two and one.ranking == two.ranking
    print(f"  Deterministic: {ok} | winner: {one.winner_strategy_id}")
    return ok


def attempt_all_unjust_deny() -> bool:
    """A field where everyone violates Justice is declined outright."""
    b1 = candid("b1", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.2})
    b2 = candid("b2", {"wisdom": 1.0, "courage": 1.0, "temperance": 1.0, "justice": 0.3})
    verdict = InMemoryArbiter().arbitrate(Dispute("pick", [b1, b2]))
    ok = verdict.decision is Verdict.DENY and verdict.winner_strategy_id is None
    print(f"  Decision: {verdict.decision.value} | winner: {verdict.winner_strategy_id}")
    return ok


def attempt_empty_declines() -> bool:
    """No candidates → the dispute is declined (DENY), not an error."""
    verdict = InMemoryArbiter().arbitrate(Dispute("pick", []))
    ok = verdict.decision is Verdict.DENY and verdict.winner_strategy_id is None
    print(f"  Empty field decision: {verdict.decision.value}")
    return ok


def attempt_keyword_fallback() -> bool:
    """Scoring drives deterministically from output keywords without metadata."""
    legal = CandidateOutput(
        strategy_id="legal", output="impartial, fair, lawful, consent", metadata={}
    )
    verdict = InMemoryArbiter().arbitrate(Dispute("pick", [legal]))
    justice = verdict.scorecards[0].virtue_scores["justice"]
    ok = justice > 0.0 and verdict.decision is Verdict.DENY
    print(f"  Justice signal: {justice:.2f} | decision: {verdict.decision.value}")
    return ok


def attempt_malformed_rejected() -> bool:
    """An empty-goal dispute is rejected with AreteError."""
    try:
        InMemoryArbiter().arbitrate(Dispute("   ", [candid("a", perfect())]))
        print("  FAIL: malformed dispute accepted")
        return False
    except AreteError:
        print("  OK: empty-goal dispute rejected with AreteError")
        return True


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeAreteArbitration",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAreteArbitration", "time": "0"})
        if not ok:
            ET.SubElement(
                testcase,
                "failure",
                {"message": f"Check {name} failed", "type": "AssertionError"},
            )
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Non-compensatory: unjust best candidate loses", attempt_non_compensatory),
    ("Excellence tie ruled DEFER, never guessed", attempt_tie_defers),
    ("Virtue weights change the winner", attempt_weights_change_winner),
    ("Arbitration is deterministic across runs", attempt_deterministic),
    ("Field of all-unjust candidates is declined", attempt_all_unjust_deny),
    ("Empty dispute is declined, not an error", attempt_empty_declines),
    ("Keyword fallback drives scoring", attempt_keyword_fallback),
    ("Malformed dispute rejected with AreteError", attempt_malformed_rejected),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="ARETĒ Arbitration Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: ARETĒ Arbitration — Deterministic & Non-Compensatory")
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
        print("\nALL CHECKS PASSED - ARETE ARBITRATION IS DETERMINISTIC AND NON-COMPENSATORY")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())