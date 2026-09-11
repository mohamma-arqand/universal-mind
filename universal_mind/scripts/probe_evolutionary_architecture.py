#!/usr/bin/env python3
"""Probe: evolutionary architecture — insights route back into generation.

The mind already produces knowledge every cycle (rejected branches, bar, budget,
health), but that knowledge used to be a dead end. This probe proves the feedback
loop is now closed: a shaped PowerGenerator bakes the mind's insights into the
next generation's description, and the emitted power reflects those constraints.
Exit non-zero unless all hold.
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
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.generator import PowerZeroGenerator
from universal_mind.powers.introspection_feedback import (
    extract_insights,
    make_insight_driven_generator,
)


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def check_insights_are_extracted() -> bool:
    loop = _loop()
    insight = extract_insights(loop)
    ok = insight.acceptance_bar == 0.9 and insight.budget == 100.0
    print(f"  insights extracted from reactive state: {ok}")
    return ok


def check_shaped_generator_feeds_power_zero() -> bool:
    loop = _loop()
    loop.tighten(bar_step=0.1)  # unhealthy state
    gen = make_insight_driven_generator(loop)
    # Feed the shaped generator through the real Power Zero pipeline.
    result = PowerZeroGenerator(generator=gen).generate("sum-power", "sum the numbers")
    ok = result.accepted and result.minted is not None
    print(f"  insight-shaped generator produces an accepted, minted power: {ok}")
    return ok


def check_insight_changes_description() -> bool:
    loop = _loop()
    loop.tighten(bar_step=0.1)
    gen = make_insight_driven_generator(loop)
    source, _ = gen("count-power", "count the items")
    # The unhealthy insight rewrote the description -> the generated source carries
    # the caution wording in its header comment.
    ok = "economical" in source.lower()
    print(f"  unhealthy insight constrains the generated description: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeEvolutionaryArchitecture",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeEvolutionaryArchitecture", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Insights are extracted", check_insights_are_extracted),
    ("Shaped generator feeds Power Zero", check_shaped_generator_feeds_power_zero),
    ("Insight constrains the generated description", check_insight_changes_description),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evolutionary architecture probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: EVOLUTIONARY ARCHITECTURE (insight → generation feedback)")
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

    print("\nALL CHECKS PASSED - THE MIND LEARNS ACROSS GENERATIONS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())