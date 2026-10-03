#!/usr/bin/env python3
"""Probe: the OPERATOR EXPERIENCE — five commands, one sitting, all real.

The operator's whole journey in one live pass — the exact sentences they
would type, run through the REAL engine in sequence, each narrated:

  1. MAKE      «گزارش کامل فروش با ۴ و ۹ بساز» (4 programs, 2 flows)
  2. READ      «نمودار خطی از ۲ و ۵ و ۹ بساز و ساختارش را بخوان» (see + understand)
  3. STORE     «میانگین ۱۲ و ۲۴ را حساب کن و در سیاسوی بریز» (the 19th)
  4. STATUS    «وضعیت» (the agent's board)
  5. RESUME    «ادامه بده» (the recovery word — honest when nothing stopped)

Exit non-zero unless the whole sitting works.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_make() -> bool:
    """«گزارش کامل ...» — the everything-chain still works after all growth."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("گزارش کامل فروش با ۴ و ۹ بساز")
    ok = payload["ok"] is True and len(payload["route"]) >= 3
    ok = ok and any("→ pdf" in f for f in payload.get("flows", []))
    print(f"  route: {payload['route']} | flows: {len(payload.get('flows', []))}")
    return bool(ok)


def check_read_and_understand() -> bool:
    """«ساختارش را بخوان» — perception still closes after all growth."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی از ۲ و ۵ و ۹ بساز و ساختارش را بخوان")
    ok = payload["ok"] is True
    # the vision result carries the structure dict
    vision = payload.get("result", {}).get("vision", {})
    ok = isinstance(vision, dict) and ("dominant_colors" in vision or "shape" in vision)
    print(f"  vision keys: {list(vision)[:3] if isinstance(vision, dict) else vision}")
    return bool(ok)


def check_store_in_csv() -> bool:
    """«در سیاسوی بریز» — the 19th capability in a live chain."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین ۱۲ و ۲۴ را حساب کن و در سیاسوی بریز")
    ok = payload["ok"] is True and payload["route"] == ["data", "csv"]
    csv_out = payload.get("result", {}).get("csv", {})
    ok = ok and csv_out.get("rows") == 6
    print(f"  csv rows: {csv_out.get('rows')} | bytes: {csv_out.get('bytes')}")
    return bool(ok)


def check_status_board() -> bool:
    """«وضعیت» — the agent's board answers."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("وضعیت")
    ok = payload["ok"] is True and payload["route"] == ["goal"]
    ok = ok and bool(payload.get("agent_report", ""))
    first = payload["agent_report"].splitlines()[0][:60]
    print(f"  board[0]: {first}")
    return bool(ok)


def check_resume_word() -> bool:
    """«ادامه بده» — the recovery word answers honestly in every state."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("ادامه بده")
    ok = payload["ok"] is True and payload["route"] == ["goal"]
    ok = ok and ("هدفی متوقف نشده" in payload["agent_report"] or "گام" in payload["agent_report"])
    first = payload["agent_report"].splitlines()[0][:60]
    print(f"  resume: {first}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeOperatorExperience",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeOperatorExperience", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("MAKE: the everything-chain (گزارش کامل)", check_make),
    ("READ+UNDERSTAND: perception closes (ساختارش را بخوان)", check_read_and_understand),
    ("STORE: the csv chain (در سیاسوی بریز)", check_store_in_csv),
    ("STATUS: the agent's board (وضعیت)", check_status_board),
    ("RESUME: the recovery word (ادامه بده)", check_resume_word),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Operator-experience probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE OPERATOR EXPERIENCE (پنج فرمان، یک نشست، همه واقعی)")
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

    print("\nALL CHECKS PASSED — THE SITTING WORKS END TO END" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())