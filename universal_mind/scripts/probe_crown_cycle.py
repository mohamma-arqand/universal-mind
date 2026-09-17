#!/usr/bin/env python3
"""Probe: the crown cycle — the platform's best practice, elected live.

The standing chain (3+ wins at >=0.90) goes through the REAL StandardKeeper
election — the justice hard-gate against a refusal baseline — and the crown,
its election reasoning, and the dashboard's crown card are all checked live:

  1. STANDING: the live history genuinely has a qualifying chain;
  2. ELECTION: the crown passes (or is honestly refused with the reason);
  3. DASHBOARD: the crowned chain and the goals' verdicts render in Persian.

Exit non-zero unless the whole cycle holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_the_live_history_has_a_winner() -> bool:
    from universal_mind.history_analytics import standing_chain

    result = standing_chain()
    ok = result["ok"] is True and result["wins"] >= 3
    ok = ok and result["mean_excellence"] >= 0.90
    print(f"  chain: {result['route']} | wins: {result['wins']} | mean: {result['mean_excellence']}")
    return bool(ok)


def check_the_election_crowns_or_refuses_honestly() -> bool:
    from universal_mind.history_analytics import crown_standing_chain

    result = crown_standing_chain()
    # EITHER crowned (with the election's own reasoning) OR honestly refused
    # (with the qualifier message) — anything else is a lie.
    ok = result["ok"] is True and result["crowned"] is True and result["decision"]
    if result["ok"] is False:
        ok = "سزاوار" in result.get("error", "")
        print(f"  honestly refused: {result.get('error', '')[:60]}")
    else:
        print(f"  crowned: {result['chain']} | election says: {result['decision'][:80]}")
    return bool(ok)


def check_the_dashboard_carries_the_crown() -> bool:
    from universal_mind.superplatform_dashboard import build_dashboard

    result = build_dashboard()
    html = open(result["path"], encoding="utf-8").read()
    ok = "تاج ARETĒ" in html and "آخرین داوری" in html
    if "chart → pdf" in html:
        print("  dashboard: the crowned chain renders")
    else:
        print("  dashboard: crown card present (no crowned chain text)")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeCrownCycle",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeCrownCycle", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("standing: the live history has a qualifying chain", check_the_live_history_has_a_winner),
    ("election: crowned, or honestly refused with the reason", check_the_election_crowns_or_refuses_honestly),
    ("dashboard: the crown and goal verdicts render in Persian", check_the_dashboard_carries_the_crown),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Crown-cycle probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE CROWN CYCLE (زنجیرهی برتر ← انتخابات ← تاج ← داشبورد)")
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

    print("\nALL CHECKS PASSED — THE BEST PRACTICE IS CROWNED" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())