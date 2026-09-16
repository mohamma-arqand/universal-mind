#!/usr/bin/env python3
"""Probe: the full Persian loop — route, extract, run, report, learn.

The strongest end-to-end proof of the Persian layer: a real Persian command is
routed, its parameters extracted from the sentence, the routed chain executed
through the real engine, the result rendered as a fluent Persian report, the run
recorded to history, and the advisor able to recommend from that history.
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


def check_full_persian_loop() -> bool:
    import uuid

    from universal_mind.persian_report import persian_report
    from universal_mind.persian_router import route_and_run
    from universal_mind.run_history import ChainAdvisor

    marker = uuid.uuid4().hex[:6]
    command = f"میانگین ۸ و ۱۲ و ۱۶ را حساب کن، نمودارش کن و ذخیره کن {marker}"
    payload = route_and_run(command)

    ok = payload["ok"] is True
    print(f"  routed: {' → '.join(payload['route'])}")
    ok = ok and set(payload["route"]) == {"data", "chart", "database"}
    ok = ok and payload["result"]["data"]["mean"] == 12.0  # extracted numbers really used
    ok = ok and payload["result"]["chart"]["bytes"] > 0
    ok = ok and payload["result"]["database"]["inserted"] == 3

    report = persian_report(payload)
    ok = ok and report.startswith("✅") and "میانگین" in report
    print(f"  report rendered: {report.splitlines()[1][:60]}...")

    advice = ChainAdvisor().advise(f"میانگین و نمودار {marker}")
    ok = ok and advice is not None and "data" in advice.route
    print(f"  advisor learned: {advice.route if advice else None}")
    return bool(ok)


def check_history_analytics_real() -> bool:
    from universal_mind.history_analytics import analytics_report, analyze_history

    stats = analyze_history()
    ok = stats.total_runs > 0 and stats.success_rate > 0.0
    print(f"  history: {stats.total_runs} runs, success {stats.success_rate:.0%}")
    report = analytics_report(stats)
    ok = ok and "نرخ موفقیت" in report
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbePersianLoop",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbePersianLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("full persian loop (route→extract→run→report→learn)", check_full_persian_loop),
    ("history analytics over real runs", check_history_analytics_real),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Persian loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: PERSIAN LOOP (فرمان فارسی → اجرا → گزارش → یادگیری)")
    print("=" * 64)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\\n--- {name} ---")
        try:
            results.append((name, fn()))
        except Exception as exc:  # noqa: BLE001
            print(f"  check raised: {exc!r}")
            results.append((name, False))

    all_ok = all(ok for _, ok in results)
    for name, result in results:
        print(f"\\n  {name}: {'OK' if result else 'FAILED'}")

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\\nJUnit XML written to {args.junit_xml}")

    print("\\nALL CHECKS PASSED — THE MIND SPEAKS PERSIAN END TO END" if all_ok else "\\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())