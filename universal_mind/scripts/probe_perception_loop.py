#!/usr/bin/env python3
"""Probe: the perception loop — the platform SEES and UNDERSTANDS its own work.

The deepest closed loop the platform carries, proven live end to end:
  MAKE      a real chart (matplotlib)
  LOOK      real OpenCV statistics on that very PNG (vision flow)
  UNDERSTAND chart structure detection (dominant colors, long lines, ink)
  REPORT    everything flows into ONE Persian RTL PDF (table + image inside)
  NARRATE   the fluent Persian report says all of it

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


def check_make_then_look() -> bool:
    """chart → vision: real OpenCV stats on the chart the chain itself made."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی بساز و تحلیل تصویرش کن")
    ok = payload["ok"] is True
    ok = ok and payload["route"] == ["chart", "vision"]
    ok = ok and any("→ بینایی" in f for f in payload["flows"])
    vision_out = payload["result"].get("vision", {})
    ok = ok and isinstance(vision_out, dict) and "shape" in vision_out
    print(f"  route: {payload['route']} | saw shape: {vision_out.get('shape')}")
    return bool(ok)


def check_understand_structure() -> bool:
    """chart_structure on the chain's own chart — real understanding."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی بساز و ساختارش را بخوان")
    ok = payload["ok"] is True
    vision_out = payload["result"].get("vision", {})
    ok = ok and isinstance(vision_out, dict) and "dominant_colors" in vision_out
    if ok:
        colors = vision_out["dominant_colors"]
        ok = ok and vision_out["long_lines"] >= 2 and colors[0]["share"] > 0.5
    print(f"  lines: {vision_out.get('long_lines')} | dominant share: "
          f"{(vision_out.get('dominant_colors') or [{}])[0].get('share')}")
    return bool(ok)


def check_report_fuses_everything() -> bool:
    """chart → vision → pdf: the report carries BOTH the table and the image."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی بساز و تحلیل تصویرش کن و گزارشش کن")
    ok = payload["ok"] is True
    ok = ok and payload["route"] == ["chart", "vision", "pdf"]
    ok = ok and any("جدول آمار + نمودار درون گزارش" in f for f in payload["flows"])
    pdf = payload["result"].get("pdf", {})
    ok = ok and pdf.get("bytes", 0) > 45000  # both parts are really inside
    print(f"  route: {payload['route']} | pdf bytes: {pdf.get('bytes')}")
    return bool(ok)


def check_narration_is_fluent_persian() -> bool:
    """The report says what was seen and understood — in Persian, no leaks."""
    from universal_mind.persian_report import persian_report
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی بساز و ساختارش را بخوان")
    report = persian_report(payload)
    ok = "ساختار تصویر خوانده شد" in report
    ok = ok and "خطِ بلند" in report
    ok = ok and "chart" not in report and "vision" not in report
    first = " / ".join(report.splitlines()[:2])
    print(f"  report: {first[:90]}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbePerceptionLoop",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbePerceptionLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("make → look: vision stats on the chain's own chart", check_make_then_look),
    ("understand: chart structure detection is real", check_understand_structure),
    ("report fuses table + image in ONE Persian pdf", check_report_fuses_everything),
    ("narration: fluent Persian, no English leaks", check_narration_is_fluent_persian),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Perception-loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: PERCEPTION LOOP (ساخت ← بینایی ← فهم ← گزارش)")
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

    print("\nALL CHECKS PASSED — THE MIND SEES AND UNDERSTANDS ITS OWN WORK" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())