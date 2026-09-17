#!/usr/bin/env python3
"""Probe: the reading loop — make → look → understand → READ → narrate.

The OCR capability closes the deepest perception cycle the platform has:
it MAKES a chart, LOOKS at it (OpenCV), UNDERSTANDS its structure, READS its
text (Windows OCR), and narrates all of it in Persian. This probe locks each
stage live:

1. REAL READ: a Pillow-rendered PNG with known text → the Windows OCR engine
   extracts exactly that text (never a fabricated string);
2. THE CHAIN FLOW: chart → ocr — the platform reads its OWN just-made chart
   (the title text it drew comes back);
3. HONEST EMPTY: a blank image reads as ok-with-nothing (never a fake);
4. THE FULL CYCLE: one Persian command runs make→look→understand→read and
   the fluent Persian report narrates every stage.

Exit non-zero unless every stage holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _text_image(text: str) -> Path:
    from PIL import Image, ImageDraw

    folder = tempfile.mkdtemp(prefix="um-probe-ocr-")
    img_path = Path(folder) / "note.png"
    img = Image.new("RGB", (460, 130), "white")
    ImageDraw.Draw(img).text((25, 45), text, fill="black")
    img.save(img_path)
    return img_path


def check_real_read() -> bool:
    """Known text in pixels → exactly that text extracted."""
    from universal_mind.ocr_tool import OcrTool

    img = _text_image("UNIVERSAL MIND 42")
    result = OcrTool().read(str(img))
    ok = result["ok"] is True and result["language"]  # the recognizer reported
    text = result["text"].upper().replace(" ", "")
    ok = ok and "UNIVERSAL" in text and "42" in text
    print(f"  read: {result['text']!r} ({result['language']})")
    return bool(ok)


def check_chain_reads_its_own_chart() -> bool:
    """chart → ocr: the platform reads the chart it just drew."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

    syn = orchestrate(
        real_tool_registry(), ["chart", "ocr"],
        connector_factory=real_connector_factory, flow=True,
        command="نمودار بساز و متنش را بخوان",
        capability_params={"chart": {"operation": "line", "title": "SALES REPORT"}},
    )
    ok = syn.ok is True
    flows = syn.output.get("flows", [])
    ok = ok and any("→ متنخوان" in f for f in flows)
    ocr_out = syn.output["synthesized_from"].get("ocr", {})
    # the chart's own title really came back from the pixels
    ok = ok and "SALES" in str(ocr_out.get("text", "")).upper()
    print(f"  flow: {flows} | read: {str(ocr_out.get('text', ''))[:50]!r}")
    return bool(ok)


def check_blank_is_honest_empty() -> bool:
    """A blank image: ok, empty, honestly narrated — never a fake."""
    from PIL import Image

    from universal_mind.ocr_tool import OcrTool

    folder = tempfile.mkdtemp(prefix="um-probe-blank-")
    img_path = os.path.join(folder, "blank.png")
    Image.new("RGB", (80, 80), "white").save(img_path)
    result = OcrTool().read(img_path)
    ok = result["ok"] is True and result["text"].strip() == ""
    print(f"  blank: ok={result['ok']} text={result['text']!r}")
    return bool(ok)


def check_full_cycle_narrates_in_persian() -> bool:
    """One command, the whole cycle, narrated in Persian without leaks."""
    from universal_mind.persian_report import persian_report
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی بساز و ساختارش را بخوان و متنش را بخوان")
    report = persian_report(payload)
    ok = payload["ok"] is True
    ok = ok and "ساختار تصویر خوانده شد" in report       # understand
    ok = ok and "متنِ تصویر خوانده شد" in report          # read
    # No English in the SYSTEM's own narration lines. (OCR-extracted content is
    # the image's real text — quoted material, not a leak: the chart drew its
    # own English title, and reading it honestly is the feature.)
    system_lines = [ln for ln in report.splitlines() if not ln.startswith("• متنِ تصویر")]
    joined = "\n".join(system_lines)
    ok = ok and "chart" not in joined and "ocr" not in joined
    first = " / ".join(report.splitlines()[:2])
    print(f"  report: {first[:90]}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeReadingLoop",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeReadingLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("real read: known text extracted from pixels", check_real_read),
    ("chain flow: the platform reads its own chart", check_chain_reads_its_own_chart),
    ("blank image: honest empty, never a fake", check_blank_is_honest_empty),
    ("full cycle: make→look→understand→read, narrated in Persian", check_full_cycle_narrates_in_persian),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Reading-loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE READING LOOP (ساخت ← بینایی ← فهم ← خواندن)")
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

    print("\nALL CHECKS PASSED — THE MIND READS WHAT IT MAKES" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())