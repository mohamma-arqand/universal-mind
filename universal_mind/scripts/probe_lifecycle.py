#!/usr/bin/env python3
"""Probe: the lifecycle loop — mint → remember → consent, on one ledger."""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.feedback import HumanVerdict
from universal_mind.lifecycle import Lifecycle
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.power_zero import PowerZero


def attempt_mint_remember_promote() -> bool:
    """With consent, a working power is minted, remembered, and promoted."""
    PowerZero.reset_minted()
    turn = Lifecycle(InMemoryStore(), consent=lambda p, k: HumanVerdict.CONSENT).run(
        "loop-power", "probe lifecycle power"
    )
    ok = turn.generated.accepted and turn.remembered and turn.promoted
    print(f"  mint+remember+promote in one ledger: {ok}")
    return ok


def attempt_deny_blocks_promotion() -> bool:
    """Deny-by-default keeps a power provisional, but the mind still remembers it."""
    PowerZero.reset_minted()
    turn = Lifecycle(InMemoryStore()).run("pending-power", "pending")
    ok = turn.remembered and not turn.promoted and turn.consent_outcome.human_verdict is HumanVerdict.VETO
    print(f"  deny-by-default remembers but does not promote: {ok}")
    return ok


def attempt_rejected_end_cleanly() -> bool:
    """A rejected power ends the turn with no partial state."""
    PowerZero.reset_minted()
    import universal_mind.powers.generator as gen

    lc = Lifecycle(
        InMemoryStore(),
        consent=lambda p, k: HumanVerdict.CONSENT,
        generator=gen.PowerZeroGenerator(benchmark=lambda fn, exp: 0.0),
    )
    turn = lc.run("doomed", "fails benchmark")
    ok = not turn.generated.accepted and not turn.remembered and not turn.promoted
    print(f"  rejected power ends the turn cleanly: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeLifecycle",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeLifecycle", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Mint + remember + promote in one ledger", attempt_mint_remember_promote),
    ("Deny-by-default remembers without promoting", attempt_deny_blocks_promotion),
    ("Rejected power ends the turn cleanly", attempt_rejected_end_cleanly),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Lifecycle loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: LIFECYCLE — mint → remember → consent, one closed loop")
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
        print(f"  {name}: {'OK' if result else 'FAILED'}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - THE MIND GROWS AS ONE FLOW")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())