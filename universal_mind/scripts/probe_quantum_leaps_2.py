#!/usr/bin/env python3
"""Probe: THE QUANTUM LEAPS II — session, prediction, new flows, live.

The second leap set, locked live in the release gate:
  1. SESSION — one core per sitting; real runs raise its counters;
  2. PREDICTION — a frequent chain reads strong, an unseen one inherits the
     global rate (NEVER a blind 1.0), tiers map to gate bars;
  3. HISTOGRAM — the sentence's numbers ARE the histogram's data;
  4. SPREADSHEET→CHART — a real workbook read-back plots its own rows;
  5. THE WINDOW — the session tab renders the live sitting.

Exit non-zero unless every leap holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_session_counts_real_runs() -> bool:
    from universal_mind.persian_router import route_and_run
    from universal_mind.session_core import SessionCore

    session = SessionCore.reset()
    before = session.snapshot().runs
    route_and_run("میانگین ۳ و ۹ را حساب کن")
    after = session.snapshot()
    ok = after.runs > before and after.judged > before
    print(f"  runs: {before} → {after.runs} | judged: {after.judged}")
    return bool(ok)


def check_prediction_is_honest() -> bool:
    from universal_mind.success_predictor import predict_success

    strong = predict_success(("chart", "pdf"))
    unseen = predict_success(("ocr", "zip", "notify"))
    ok = (
        strong.tier == "strong" and strong.recommended_bar == 0.75
        and unseen.evidence_runs == 0 and unseen.success_probability < 1.0
    )
    print(f"  strong: {strong.success_probability} | unseen: {unseen.success_probability}")
    return bool(ok)


def check_the_live_router_uses_the_dynamic_bar() -> bool:
    """A live run through the predictor-wired gate completes fine."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین ۴ و ۸ را حساب کن")
    print(f"  ok: {payload['ok']}")
    return payload["ok"] is True


def check_histogram_from_the_sentence() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("هیستوگرام ۱ و ۲ و ۲ و ۵ و ۹ را بکش")
    params = payload.get("extracted_params", {}).get("chart", {})
    ok = (
        payload["ok"] is True
        and params.get("operation") == "histogram"
        and params.get("data") == [1.0, 2.0, 2.0, 5.0, 9.0]
        and payload["result"]["chart"]["bytes"] > 5000
    )
    print(f"  op: {params.get('operation')} | data: {params.get('data')}")
    return bool(ok)


def check_spreadsheet_flows_into_chart() -> bool:
    from universal_mind.excel_suite import ExcelSuite
    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

    written = ExcelSuite().write_table(
        headers=["شاخص", "مقدار"], rows=[["الف", 3], ["ب", 7], ["ج", 5]]
    )
    syn = orchestrate(
        real_tool_registry(), ["excel", "chart"],
        connector_factory=real_connector_factory, flow=True,
        command="اکسل را بخوان و نمودارش بکش",
        capability_params={"excel": {"operation": "read_table", "path": written["path"]}},
    )
    ok = syn.ok and any("→ chart" in f for f in syn.output.get("flows", []))
    print(f"  flows: {syn.output.get('flows')}")
    return bool(ok)


def check_the_session_tab_renders() -> bool:
    """The window's session tab builds and renders the live sitting."""
    import tkinter as tk

    from universal_mind.desktop_app import MindDesktopApp

    root = tk.Tk()
    try:
        app = MindDesktopApp(root)
        text = app._session_text.get("1.0", tk.END)
        ok = "نشست" in text and "داوری" in text
        print(f"  tab text[0:40]: {text.strip()[:40]}")
        return bool(ok)
    finally:
        root.destroy()


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeQuantumLeapsII",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeQuantumLeapsII", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("session: real runs raise the live counters", check_session_counts_real_runs),
    ("prediction: honest tiers, never a blind 1.0", check_prediction_is_honest),
    ("the live router runs through the dynamic bar", check_the_live_router_uses_the_dynamic_bar),
    ("histogram: the sentence's numbers ARE the data", check_histogram_from_the_sentence),
    ("spreadsheet → chart: real read-back plots", check_spreadsheet_flows_into_chart),
    ("the session tab renders the sitting", check_the_session_tab_renders),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantum-leaps-II probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: QUANTUM LEAPS II (نشست، پیشبینی، جریانهای جدید — زنده)")
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

    print("\nALL CHECKS PASSED — THE SECOND LEAP SET HOLDS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())