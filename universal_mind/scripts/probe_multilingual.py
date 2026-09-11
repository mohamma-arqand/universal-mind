#!/usr/bin/env python3
"""Probe: multilingual understanding — a language-independent intent layer.

The mind should not care which human language a goal arrives in. This probe proves
English and Persian utterances converge to the SAME canonical action, so any
language lands in the same execution loop. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.mouth.multilingual import normalize_intent


def check_english_and_persian_converge() -> bool:
    en = normalize_intent("summarize the report")
    fa = normalize_intent("گزارش را خلاصه کن")
    ok = en.action == fa.action == "summarize"
    print(f"  English and Persian converge on the same action: {ok}")
    return ok


def check_language_is_detected() -> bool:
    en = normalize_intent("summarize the report")
    fa = normalize_intent("گزارش را خلاصه کن")
    ok = en.source_language == "en" and fa.source_language == "fa"
    print(f"  source language is detected: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeMultilingual",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeMultilingual", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("English and Persian converge", check_english_and_persian_converge),
    ("Source language is detected", check_language_is_detected),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Multilingual probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: MULTILINGUAL UNDERSTANDING (any language -> one loop)")
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

    print("\nALL CHECKS PASSED - THE MIND SPEAKS EVERY LANGUAGE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())