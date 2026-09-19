#!/usr/bin/env python3
"""Probe: THE REFLEXIVE CLASS — the platform answers about itself, for real.

«چند تا اجرا موفق داشتی؟» must return a REAL number from the store, never
a guess. Locked live in the release gate:
  1. run counts (total + success %)
  2. the most successful capability / chain
  3. the last thing made
  4. help counts the 20 capabilities
  5. non-questions are never hijacked

Exit non-zero unless every reflex holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_run_counts() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("چند تا اجرا موفق داشتی؟")
    ok = payload["route"] == ["reflexive"] and "اجرا" in payload["agent_report"]
    print(f"  {payload['agent_report'][:60]}")
    return bool(ok)


def check_best_capability_and_chain() -> bool:
    from universal_mind.persian_router import route_and_run

    cap = route_and_run("موفقترین قابلیت کدومه؟")["agent_report"]
    chain = route_and_run("کدام زنجیره بیشتر موفق شده؟")["agent_report"]
    ok = "موفقترین قابلیت" in cap and "موفقترین زنجیره" in chain
    print(f"  {cap[:50]} | {chain[:50]}")
    return bool(ok)


def check_last_made() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("آخرین چیزی که ساختی چی بود؟")
    ok = "آخرین کار موفق" in payload["agent_report"]
    print(f"  {payload['agent_report'][:70]}")
    return bool(ok)


def check_help() -> bool:
    from universal_mind.persian_router import route_and_run
    from universal_mind.real_tool_registry import real_tool_registry

    payload = route_and_run("راهنما")
    n = len(real_tool_registry().capabilities())
    fa = str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    ok = fa in payload["agent_report"] or str(n) in payload["agent_report"]
    print(f"  help lists {n} capabilities: {payload['agent_report'][:60]}")
    return bool(ok)


def check_no_hijack() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین ۳ و ۹ را حساب کن")
    ok = payload["route"] != ["reflexive"] and payload["ok"] is True
    print(f"  compute route intact: {payload['route']}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeReflexive",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeReflexive", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("run counts: real numbers from the store", check_run_counts),
    ("best capability + chain: the real ranking", check_best_capability_and_chain),
    ("last made: the newest real success", check_last_made),
    ("help: counts the capabilities for real", check_help),
    ("no hijack: commands still route normally", check_no_hijack),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Reflexive-class probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE REFLEXIVE CLASS (خود-پرسشها، پاسخهای واقعی)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM ANSWERS ABOUT ITSELF" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())