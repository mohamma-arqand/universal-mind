#!/usr/bin/env python3
"""Probe: temporal awareness — what time is it, and what does that mean.

A clock gives the raw instant; a mind needs its meaning. This probe proves the
temporal-awareness layer derives decision-relevant signals (business hours vs
off-hours, weekend, freshness of a reference) from an injectable clock — entirely
deterministic, no wall-clock in the assertions. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.core.clock import FrozenClock
from universal_mind.core.temporal_awareness import derive_temporal_context


def _clock(iso: str) -> FrozenClock:
    return FrozenClock(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc))


def check_business_vs_off_hours() -> bool:
    business = derive_temporal_context(_clock("2026-09-07T10:00:00"))
    off = derive_temporal_context(_clock("2026-09-07T20:00:00"))
    ok = business.is_business_hours is True and off.is_business_hours is False
    print(f"  business vs off-hours is distinguished: {ok}")
    return ok


def check_weekend_is_detected() -> bool:
    ctx = derive_temporal_context(_clock("2026-09-13T10:00:00"))
    ok = ctx.is_weekend is True and ctx.is_business_hours is False
    print(f"  weekend is detected: {ok}")
    return ok


def check_freshness_is_computed() -> bool:
    ref = datetime.fromisoformat("2026-09-07T08:00:00").replace(tzinfo=timezone.utc)
    ctx = derive_temporal_context(_clock("2026-09-07T10:00:00"), reference=ref)
    ok = abs(ctx.freshness_hours - 2.0) < 0.01
    print(f"  freshness of a reference is computed: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeTemporalAwareness",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeTemporalAwareness", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Business vs off-hours is distinguished", check_business_vs_off_hours),
    ("Weekend is detected", check_weekend_is_detected),
    ("Freshness is computed", check_freshness_is_computed),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Temporal awareness probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: TEMPORAL AWARENESS (time with meaning)")
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

    print("\nALL CHECKS PASSED - THE MIND KNOWS WHAT TIME MEANS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())