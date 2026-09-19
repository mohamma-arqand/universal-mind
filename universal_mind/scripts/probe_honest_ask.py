#!/usr/bin/env python3
"""Probe: the honest-ask webfetch + the flow-evidence loop, live.

Locked in the release gate:
  1. A url-less webfetch asks IN PERSIAN with the remedy — never a bare
     English 'no url given'.
  2. A real two-capability run leaves its flows in the history (the
     flow-evidence column exists and is populated live).
  3. The computed series is plotted (the compute→chart flow fires).

Exit non-zero unless every hold is green.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_the_honest_ask() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("خلاصه سایت و گزارشش کن")
    err = (payload.get("errors") or {}).get("webfetch", "")
    ok = "کدام سایت" in err and "آدرس" in err
    print(f"  ask: {err[:70]!r}")
    return bool(ok)


def check_the_flow_evidence_loop() -> bool:
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    route_and_run("میانگین ۴ و ۸ را حساب کن و نمودارش را بکش")
    row = DatabaseSuite(persistent=True).query(
        "SELECT route, flows FROM run_history WHERE flows != '' ORDER BY id DESC LIMIT 1"
    )["rows"]
    ok = bool(row) and "→ chart" in row[0]["flows"]
    print(f"  history flows: {row[0]['flows'][:60]!r}" if row else "  NO flows recorded")
    return bool(ok)


def check_the_computed_series() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین ۵ و ۹ را حساب کن و نمودارش را بکش")
    flows = payload.get("flows") or []
    ok = payload["ok"] is True and any("→ chart" in f for f in flows)
    print(f"  flows: {flows}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeHonestAsk",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeHonestAsk", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("honest ask: url-less webfetch asks in Persian", check_the_honest_ask),
    ("flow-evidence: real runs populate the column", check_the_flow_evidence_loop),
    ("computed series: the compute→chart flow fires", check_the_computed_series),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Honest-ask probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE HONEST ASK (پرسش صادقانه، حلقهی شواهد جریان)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM ASKS HONESTLY, LEARNS CONTINUOUSLY" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())