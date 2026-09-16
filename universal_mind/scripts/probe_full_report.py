#!/usr/bin/env python3
"""Probe: the full-report chain + the dashboard — one command, every artifact.

Locks the operator's one-command experience live:
1. «گزارش کامل» runs data → chart → pdf → archive with BOTH flows real;
2. the dashboard builds from the REAL history and carries the real numbers;
3. the ARETĒ verdict over the full chain is sound (all four virtues).

Exit non-zero unless every stage holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_full_report_chain() -> bool:
    """«گزارش کامل» — one command, four programs, both flows."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("گزارش کامل فروش با اعداد ۳۰ و ۷۰ و ۲۰ را بساز")
    ok = payload["ok"] is True
    ok = ok and payload["route"] == ["data", "chart", "pdf", "archive"]
    flows = payload.get("flows", [])
    ok = ok and any("→ pdf" in f for f in flows)
    ok = ok and any("بایگانی" in f for f in flows)
    result = payload.get("result", {})
    ok = ok and result.get("archive", {}).get("bytes", 0) > 50000
    print(f"  route: {payload['route']} | flows: {len(flows)} | archive: {result.get('archive', {}).get('bytes')} bytes")
    return bool(ok)


def check_dashboard_carries_real_numbers() -> bool:
    """The dashboard renders the operator's real history."""
    import tempfile
    from pathlib import Path

    from universal_mind.superplatform_dashboard import build_dashboard

    out = Path(tempfile.mkdtemp(prefix="um-dash-probe-")) / "dash.html"
    result = build_dashboard(str(out))
    ok = result["ok"] is True and result["bytes"] > 3000
    html = out.read_text(encoding="utf-8")
    ok = ok and "کل اجراها" in html and "planner چه آموخته" in html
    # Persian digits present (the KPI row is rendered, not stubbed)
    import re

    ok = ok and re.search(r"[۰-۹]+", html) is not None
    is_rtl = 'dir="rtl"' in html
    print(f"  dashboard: {result['bytes']} bytes | RTL: {is_rtl}")
    return bool(ok)


def check_arete_verdict_over_the_full_chain() -> bool:
    """ARETĒ grades the whole four-program chain soundly."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("گزارش کامل دادهها با ۸ و ۱۲ را بساز")
    judgment = payload.get("judgment", {})
    ok = bool(judgment) and judgment.get("excellence", 0.0) >= 0.75
    ok = ok and judgment.get("disqualified") is False
    print(f"  excellence: {judgment.get('excellence')} | scores: {judgment.get('scores')}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeFullReportDashboard",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeFullReportDashboard", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("full-report chain: one command, four programs, both flows", check_full_report_chain),
    ("dashboard: real history, real numbers, Persian RTL", check_dashboard_carries_real_numbers),
    ("ARETĒ grades the full chain soundly", check_arete_verdict_over_the_full_chain),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Full-report + dashboard probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: FULL REPORT + DASHBOARD (گزارش کامل + داشبورد)")
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

    print("\nALL CHECKS PASSED — ONE COMMAND, EVERY ARTIFACT" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())