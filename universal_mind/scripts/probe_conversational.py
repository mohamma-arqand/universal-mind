#!/usr/bin/env python3
"""Probe: the conversational face — the operator's FIRST words get an answer.

The fresh 20-command everyday sweep found ELEVEN navigation holes. The worst
class: SMALL TALK («سلام»/«ممنون»/«کمک کن») fell through every route — a
platform that answers statistics but goes mute on the greeting is broken at
the first word. Locked live in the release gate:
  1. greetings/thanks/help/whats-up answer in fluent Persian (short, warm)
  2. real commands are never hijacked by the conversational class
  3. the memory-shaped holes closed: تحلیل→data، زیپ→archive، زمان بگیر→notify،
     دیروز-ساختی→reflexive، ترندها→the real session verdict، PDF از نتایج→real file
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


def check_small_talk_answers() -> bool:
    from universal_mind.persian_router import route_and_run

    ok = True
    for c, want in (("سلام", "سلام"), ("خسته نباشید", "خواهش"), ("ممنون", "خواهش"),
                    ("کمک کن لطفا", "فرمان"), ("دنبال چه میگردی؟", "خدمت")):
        p = route_and_run(c)
        good = p.get("route") == ["conversational"] and want in p.get("agent_report", "")
        print(f"  {c!r}: {'OK' if good else 'FAILED'} — {p.get('agent_report', '')[:45]!r}")
        ok = ok and good
    return bool(ok)


def check_no_hijack() -> bool:
    from universal_mind.persian_router import route_and_run

    for c in ("میانگین ۳ و ۹ را حساب کن", "نمودار خطی بساز", "ضرب ۶ در ۷ را حساب کن"):
        p = route_and_run(c)
        if p.get("route") == ["conversational"]:
            print(f"  HIJACKED: {c!r}")
            return False
    print("  real commands route normally")
    return True


def check_navigation_holes() -> bool:
    from universal_mind.persian_router import route_and_run

    checks = [
        ("دادههای فروش را تحلیل کن", "data"),
        ("فایلها را زیپ کن", "zip"),  # R74 — زیپ means a real .zip (the
        # world's format), never the single-file gzip the old pin expected.
        ("زمان بگیر که فردا صبح ۸ یادم بندی", "notify"),
    ]
    ok = True
    for c, cap in checks:
        p = route_and_run(c)
        good = cap in (p.get("route") or [])
        print(f"  {c[:32]!r} -> {p.get('route')}: {'OK' if good else 'FAILED'}")
        ok = ok and good
    return bool(ok)


def check_memory_reflexes() -> bool:
    from universal_mind.persian_router import route_and_run

    y = route_and_run("چیزی که دیروز ساختی رو نشونم بده")
    t = route_and_run("ترندها رو نشون بده")
    ok_y = y.get("route") == ["reflexive"] and "آخرین کار" in y.get("agent_report", "")
    ok_t = t.get("route") == ["reflexive"] and ("روند" in t.get("agent_report", "") or "روندی" in t.get("agent_report", ""))
    print(f"  دیروز: {'OK' if ok_y else 'FAILED'} — {y.get('agent_report', '')[:50]!r}")
    print(f"  ترندها: {'OK' if ok_t else 'FAILED'} — {t.get('agent_report', '')[:50]!r}")
    return bool(ok_y and ok_t)


def check_pdf_from_results() -> bool:
    from universal_mind.persian_router import route_and_run

    p = route_and_run("یک فایل PDF از نتایج بساز")
    path = (p.get("result") or {}).get("pdf", {}).get("path", "")
    ok = "pdf" in (p.get("route") or []) and p.get("ok") is True and path.lower().endswith(".pdf")
    print(f"  pdf: {'OK' if ok else 'FAILED'} — {path[:55]!r}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeConversational",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeConversational", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("small talk: every greeting gets a warm short answer", check_small_talk_answers),
    ("no hijack: real commands route normally", check_no_hijack),
    ("navigation: تحلیل/زیپ/زمانبگیر route to real capabilities", check_navigation_holes),
    ("memory reflexes: دیروز + ترندها answer with real data", check_memory_reflexes),
    ("pdf from results: a real document lands on disk", check_pdf_from_results),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversational-face probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE CONVERSATIONAL FACE (گفتار، حفرهها بسته شد)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM SPEAKS FROM THE FIRST WORD" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())