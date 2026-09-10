#!/usr/bin/env python3
"""Probe: the three self-augmenting capabilities.

Power Zero (executable), remembering Mnemosyne, and human-in-the-loop consent
are the charter's answers to "how does the system grow without external
limits?". This probe exercises all three end-to-end and exits non-zero unless
every invariant holds -- proof that each capability is real, deterministic, and
still bounded by evidence and justice.
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
from universal_mind.feedback import HumanVerdict, PromotionConsent
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.generator import PowerZeroGenerator
from universal_mind.powers.judgment import CandidateOutput
from universal_mind.powers.power_zero import PowerZero

FULL = {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0}


def attempt_power_zero_mints() -> bool:
    """A generated power is sandboxed, benchmarked, arbitrated, and minted."""
    PowerZero.reset_minted()
    result = PowerZeroGenerator().generate("probe-power", "a probe power")
    ok = result.accepted and result.minted is not None and result.minted.precedence >= 7
    print(f"  power zero minted an executable power: {ok}")
    return ok


def attempt_power_zero_respects_justice() -> bool:
    """A power that fails the justice gate is never minted."""
    PowerZero.reset_minted()
    result = PowerZeroGenerator(benchmark=lambda fn, exp: 0.0).generate("unjust", "fails")
    ok = not result.accepted and result.minted is None
    print(f"  justice gate refuses an unworthy power: {ok}")
    return ok


def attempt_mnemosyne_remembers() -> bool:
    """Mnemosyne ranks a related record above an unrelated one."""
    clock = __import__("universal_mind.core.clock", fromlist=["FrozenClock"]).FrozenClock(
        datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    store = InMemoryStore()
    m = Mnemosyne(store, clock)
    m.record(owner_id="o", kind="synthesis", payload={"goal": "write the security report"}, provenance={"p": "x"})
    m.record(owner_id="o", kind="synthesis", payload={"goal": "bake a cake"}, provenance={"p": "x"})
    hits = m.query("security report")
    ok = bool(hits) and "security" in str(hits[0].record["payload"]["goal"])
    print(f"  mnemosyne recalls the relevant record first: {ok}")
    return ok


def attempt_consent_gates_promotion() -> bool:
    """A promotion is provisional until a human consents."""
    keeper = StandardKeeper(InMemoryStore())
    consent = PromotionConsent(keeper)  # deny-by-default
    cand = CandidateOutput(strategy_id="D1", output="a", metadata={"virtues": dict(FULL)})
    out = consent.consider(cand)
    ok = out.human_verdict is HumanVerdict.VETO and out.finalized is False
    print(f"  promotion stays provisional without consent: {ok}")
    return ok


def attempt_consent_finalizes() -> bool:
    """An explicit human consent finalizes and records HUMAN evidence."""
    keeper = StandardKeeper(InMemoryStore())
    consent = PromotionConsent(keeper, consent=lambda p, k: HumanVerdict.CONSENT)
    cand = CandidateOutput(strategy_id="D1", output="a", metadata={"virtues": dict(FULL)})
    out = consent.consider(cand)
    ok = out.finalized and out.evidence.has_human()
    print(f"  explicit consent finalizes with HUMAN evidence: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeAugmentCapabilities",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAugmentCapabilities", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Power Zero mints an executable power", attempt_power_zero_mints),
    ("Power Zero respects the justice gate", attempt_power_zero_respects_justice),
    ("Mnemosyne recalls the relevant record", attempt_mnemosyne_remembers),
    ("Promotion stays provisional without consent", attempt_consent_gates_promotion),
    ("Explicit consent finalizes with HUMAN evidence", attempt_consent_finalizes),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-augmenting capabilities probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: SELF-AUGMENTING CAPABILITIES (Power Zero · Mnemosyne · Consent)")
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
        print("\nALL CHECKS PASSED - THE MIND GROWS WITHOUT LOSING ITS BOUNDS")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())