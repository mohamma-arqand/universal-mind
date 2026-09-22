#!/usr/bin/env python3
"""Probe: R37 — the living-memory flows, the spoken vocabulary, the chat tab,
the personal memory. All locked live in the release gate.

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


def check_living_memory_flows() -> bool:
    from universal_mind.orchestration import _flow_params

    ok = True
    cases = [
        ("chart", "database", [{"metric": "میانگین", "value": "4.5"}], "رکورد ذخیرهشده رسم شد"),
        ("database", "webfetch", {"preview": "محتوای صفحه برای ذخیره"}, "خواندهشده ذخیره شد"),
        ("speech", "pdfreader", {"text": "متن سند است"}, "بلند گفته شد"),
    ]
    for consumer, producer, out, want in cases:
        _, desc = _flow_params(consumer, {}, producer, out, "فرمان", ())
        good = desc is not None and want in desc
        print(f"  {producer} → {consumer}: {'OK' if good else 'FAILED'} — {desc!r}")
        ok = ok and good
    return bool(ok)


def check_string_coercion() -> bool:
    """SQLite numbers arrive as TEXT — the flow still plots them."""
    from universal_mind.orchestration import _flow_params

    params, desc = _flow_params(
        "chart", {}, "database",
        [{"metric": "a", "value": "5"}, {"metric": "b", "value": "8"}], "c", (),
    )
    ok = desc is not None and params.get("values") == [5.0, 8.0]
    print(f"  values: {params.get('values') if desc else None} — {'OK' if ok else 'FAILED'}")
    return bool(ok)


def check_spoken_vocabulary() -> bool:
    from universal_mind.persian_router import route_and_run

    ok = True
    cases = [
        # R43: «متن بنویس» = a durable document (pdf), «موسیقی پخش کن» =
        # playing a real file (media) — the old pins locked the BUGS.
        ("متن بنویس که سلام دنیا", "pdf"),
        ("این متن را برایم بفرست", "clipboard"),
        ("موسیقی پخش کن", "media"),
        ("این صفحه را ببین و بگو چه میبینی", "vision"),
    ]
    for c, cap in cases:
        p = route_and_run(c)
        good = cap in (p.get("route") or [])
        print(f"  {c[:34]!r} -> {p.get('route')}: {'OK' if good else 'FAILED'}")
        ok = ok and good
    return bool(ok)


def check_operator_preference_loop() -> bool:
    """«همیشه نمودار میله‌ای» stored → the next plain chart IS a bar;
    «نمودار خطی» still wins (explicit beats memory)."""
    from universal_mind.persian_router import route_and_run

    ack = route_and_run("همیشه نمودار میله‌ای دوست دارم")
    stored_ok = ack.get("route") == ["preference"] and "یاد گرفتم" in ack.get("agent_report", "")
    plain = route_and_run("نمودار ۱ و ۵ و ۹ را بکش")
    became_bar = plain.get("extracted_params", {}).get("chart", {}).get("operation") == "bar"
    explicit = route_and_run("نمودار خطی ۲ و ۴ را بکش")
    line_wins = explicit.get("extracted_params", {}).get("chart", {}).get("operation") == "line"
    # restore the neutral default for determinism
    route_and_run("همیشه نمودار خطی دوست دارم")
    print(f"  stored: {stored_ok} | default→bar: {became_bar} | explicit→line: {line_wins}")
    return bool(stored_ok and became_bar and line_wins)


def check_chat_tab_renders() -> bool:
    import tkinter as tk

    from universal_mind.desktop_app import MindDesktopApp

    root = tk.Tk()
    try:
        app = MindDesktopApp(root)
        log = app._chat_log.get("1.0", tk.END)
        entry_ok = bool(app._chat_entry)
        print(f"  tab log[0:50]: {log.strip()[:50]!r} | entry: {entry_ok}")
        return bool("سلام" in log and entry_ok)
    finally:
        root.destroy()


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeR37",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeR37", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("living memory: db→chart, web→db, doc→speech", check_living_memory_flows),
    ("string coercion: TEXT numbers still plot", check_string_coercion),
    ("spoken vocabulary: بنویس/بفرست/موسیقی/ببین route", check_spoken_vocabulary),
    ("preference loop: stored → applied → explicit wins", check_operator_preference_loop),
    ("chat tab: the conversation surface renders", check_chat_tab_renders),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="R37 probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: R37 — حافظهی زنده، واژگان، گفتگو، شخصیسازی")
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

    print("\nALL CHECKS PASSED — THE PLATFORM REMEMBERS, SPEAKS, PERSONALIZES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())