#!/usr/bin/env python3
"""Probe: honesty under pressure — the red-team battery, live in the gate.

The platform's core promise is NEVER fabricate. This probe fires a battery of
hostile/ambiguous/nonsense commands at the REAL engine and asserts the
honest outcome class each time — a fake success anywhere fails the release
gate. The battery mirrors tests/test_redteam_honesty.py but runs LIVE against
the real engine on every verify (the suite proves the code; the probe proves
the running system):

  1. nonsense verbs        → honest 'no capability matched'
  2. whitespace            → refused, never crashed
  3. unreachable web       → classified offline, never fake content
  4. missing files        → named file errors
  5. blank PDF            → honest empty text (no OCR blending)
  6. unknown operations   → refused by every connector
  7. URL in excel intent  → never treated as a workbook path
  8. huge numbers         → real math, never an overflow lie

Exit non-zero unless the platform stays honest across the whole battery.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_nonsense_verb() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("زوکوپرین مکیدوبالس را فریبوس کن")
    ok = payload["ok"] is False and "هیچ قابلیتی" in payload.get("error", "")
    print(f"  ok={payload['ok']} | {payload.get('error', '')[:50]}")
    return bool(ok)


def check_whitespace() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("   ")
    ok = payload["ok"] is False  # refused, and it did not crash to get here
    print(f"  ok={payload['ok']} (refused, not crashed)")
    return bool(ok)


def check_unreachable_web() -> bool:
    from universal_mind.webfetch_tool import WebFetchTool

    result = WebFetchTool().fetch("https://dead-host-zz9.example.invalid")
    ok = result["ok"] is False and result["kind"] in ("offline", "timeout")
    ok = ok and "preview" not in result  # no fabricated page content
    print(f"  ok={result['ok']} kind={result.get('kind')} | {result.get('error', '')[:40]}")
    return bool(ok)


def check_missing_files() -> bool:
    from universal_mind.ocr_tool import OcrTool
    from universal_mind.pdfreader_tool import PdfReaderTool

    ocr = OcrTool().read("Z:/none.png")
    pdf = PdfReaderTool().read_text("Z:/none.pdf")
    ok = "not found" in ocr["error"] and "not found" in pdf["error"]
    print("  ocr+pdf both name the missing file")
    return bool(ok)


def check_blank_pdf_is_honest_empty() -> bool:
    from pathlib import Path

    from reportlab.pdfgen import canvas as rl_canvas

    folder = Path(tempfile.mkdtemp(prefix="um-probe-blankpdf-"))
    pdf_path = folder / "blank.pdf"
    c = rl_canvas.Canvas(str(pdf_path))
    c.save()  # no text at all
    from universal_mind.pdfreader_tool import PdfReaderTool

    result = PdfReaderTool().read_text(str(pdf_path))
    ok = result["ok"] is True and result["text"].strip() == ""
    print(f"  ok={result['ok']} text={result['text']!r} (empty, not OCR-blended)")
    return bool(ok)


def check_unknown_operations_refused() -> bool:
    from universal_mind.excel_suite import ExcelSuiteConnector
    from universal_mind.ocr_tool import OcrToolConnector
    from universal_mind.pdfreader_tool import PdfReaderToolConnector
    from universal_mind.screenshot_tool import ScreenshotToolConnector
    from universal_mind.webfetch_tool import WebFetchToolConnector

    for conn in (ExcelSuiteConnector(), OcrToolConnector(),
                 PdfReaderToolConnector(), ScreenshotToolConnector(),
                 WebFetchToolConnector()):
        if conn.connect({}, {"operation": "تسلط-جغرافیایی"}).ok is not False:
            print(f"  {type(conn).__name__} ACCEPTED a fake operation")
            return False
    print("  all five connectors refused the fake operation")
    return True


def check_url_never_becomes_a_workbook_path() -> bool:
    from universal_mind.persian_params import extract_params

    params = extract_params("صفحه وب https://example.com را بگیر و در اکسل بریز", "excel")
    ok = params.get("operation") != "read_table"
    print(f"  excel operation={params.get('operation')} (write, not a fake read)")
    return bool(ok)


def check_huge_numbers_compute_really() -> bool:
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین 100000000000 و 200000000000 را حساب کن")
    if payload["ok"] is not True:
        print(f"  refused unexpectedly: {payload.get('errors')}")
        return False
    data = payload.get("result", {}).get("data", {})
    ok = abs(data.get("mean", -1) - 150_000_000_000) < 1e6
    print(f"  mean={data.get('mean')} (real math at scale)")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeHonestyUnderPressure",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeHonestyUnderPressure", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("nonsense verb → honest no-capability", check_nonsense_verb),
    ("whitespace → refused, not crashed", check_whitespace),
    ("unreachable web → offline, no fake content", check_unreachable_web),
    ("missing files → named, not invented", check_missing_files),
    ("blank PDF → honest empty (no OCR blending)", check_blank_pdf_is_honest_empty),
    ("unknown operations → refused by all connectors", check_unknown_operations_refused),
    ("URL → never a workbook path", check_url_never_becomes_a_workbook_path),
    ("huge numbers → real math", check_huge_numbers_compute_really),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Honesty-pressure probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: HONESTY UNDER PRESSURE (فشار صداقت — هیچ جعلی، هرگز)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM DOES NOT FABRICATE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())