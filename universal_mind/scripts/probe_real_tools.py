#!/usr/bin/env python3
"""Probe: real external tools — a genuine service behind the gateway, fail-safe.

A mind is only "capable" if it can reach out and do real work. This probe proves
the real-tool layer: a provider issues a real HTTP call to a live arithmetic
service and returns the true result, and when the service is unreachable it fails
safe to a fallback rather than crashing. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.io.real_tools import RealToolProvider, ToolService


def check_real_tool_reaches_service() -> bool:
    service = ToolService()
    url = service.start()
    try:
        provider = RealToolProvider(url)
        result = provider.compute("sum", [1.0, 2.0, 3.0])
        ok = result.ok is True and result.output == 6.0 and result.via_fallback is False
    finally:
        service.stop()
    print(f"  real HTTP call reaches the service and returns the true result: {ok}")
    return ok


def check_unreachable_fails_safe() -> bool:
    provider = RealToolProvider("http://127.0.0.1:1")
    result = provider.compute("sum", [1.0, 2.0])
    ok = result.ok is True and result.via_fallback is True
    print(f"  an unreachable tool fails safe to a fallback: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeRealTools",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeRealTools", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Real HTTP call reaches the service", check_real_tool_reaches_service),
    ("Unreachable tool fails safe", check_unreachable_fails_safe),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Real external tools probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: REAL EXTERNAL TOOLS (a genuine service, fail-safe)")
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

    print("\nALL CHECKS PASSED - THE MIND DOES REAL WORK, SAFELY" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())