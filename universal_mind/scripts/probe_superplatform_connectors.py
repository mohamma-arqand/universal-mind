#!/usr/bin/env python3
"""Probe: super-platform live connectors — the mind reaches real tools.

Phase 1 of the super-platform: prove the connectors reach the host's real tools,
not just shell echoes. A SubprocessConnector must run a real `python -c "print(2+2)"`
and get `4` back, and `git --version` must return a real version string. The COM
connector must fail *cleanly* (never hang) when its ProgID is absent. Exit non-zero
unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.connectors import ComConnector, SubprocessConnector
from universal_mind.tool_registry import ConnectionMechanism, ToolConnectionSpec


def check_subprocess_runs_real_python() -> bool:
    conn = SubprocessConnector(allowlist=("python", "git", "pwd", "echo"))
    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="python -c \"print(2+2)\"")
    result = conn.connect(spec, {})
    ok = result.ok is True and result.output == "4"
    print(f"  real python computes 2+2 via subprocess: {ok} (output={result.output!r})")
    return ok


def check_subprocess_runs_real_git() -> bool:
    conn = SubprocessConnector(allowlist=("python", "git", "pwd", "echo"))
    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="git --version")
    result = conn.connect(spec, {})
    ok = result.ok is True and "git version" in (result.output or "")
    print(f"  real git reports a version via subprocess: {ok} (output={result.output!r})")
    return ok


def check_com_fails_clean_on_missing_progid() -> bool:
    # A ProgID that does not exist must fail clean, never hang.
    conn = ComConnector()
    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.COM, prog_id="No.Such.Object.12345")
    result = conn.connect(spec, {})
    ok = result.ok is False and isinstance(result.output, (str, type(None)))
    print(f"  COM connector fails clean (no hang) on missing ProgID: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeSuperplatformConnectors",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeSuperplatformConnectors", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Real python via subprocess", check_subprocess_runs_real_python),
    ("Real git via subprocess", check_subprocess_runs_real_git),
    ("COM fails clean on missing ProgID", check_com_fails_clean_on_missing_progid),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Super-platform live-connector probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: SUPER-PLATFORM LIVE CONNECTORS (real tools on this host)")
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

    print("\nALL CHECKS PASSED — THE MIND REACHES THE HOST'S REAL TOOLS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())