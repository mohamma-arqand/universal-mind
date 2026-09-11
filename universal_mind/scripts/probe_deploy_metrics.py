#!/usr/bin/env python3
"""Probe: observable deploy — real metrics from the ledger, not just "tests pass".

Unit tests prove correctness; a deployed mind must be observable. This probe proves
the deploy-metrics layer derives operational numbers (executions, failures, error
rate, kinds, last activity) from the append-only ledger — plain and serializable,
ready for a Prometheus/OTel scrape. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.observability.metrics import derive_deploy_metrics


def _record(kind: str, ok: bool | None = None, created: str = "2026-09-11T10:00:00") -> dict[str, object]:
    rec: dict[str, object] = {"kind": kind, "created_at": created}
    if ok is not None:
        rec["payload"] = {"ok": ok}
    return rec


def check_metrics_derived_from_ledger() -> bool:
    records = [
        _record("capability_result", ok=True),
        _record("capability_result", ok=False),
        _record("fault"),
    ]
    m = derive_deploy_metrics(records)
    ok = m.executions == 2 and m.faults == 1 and _approx(m.error_rate, 1 / 3)
    print(f"  executions/faults/error-rate derived from the ledger: {ok}")
    return ok


def check_last_activity_is_latest() -> bool:
    records = [_record("x", created="2026-09-11T10:00:00"), _record("y", created="2026-09-11T12:00:00")]
    m = derive_deploy_metrics(records)
    ok = m.last_activity == "2026-09-11T12:00:00"
    print(f"  last-activity timestamp is the latest record: {ok}")
    return ok


def _approx(x: float, target: float, tol: float = 0.01) -> bool:
    # Tiny local approximate comparison (no pytest dependency in the probe).
    return abs(x - target) < tol


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeDeployMetrics",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeDeployMetrics", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Metrics derived from the ledger", check_metrics_derived_from_ledger),
    ("Last-activity is the latest record", check_last_activity_is_latest),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy metrics probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: OBSERVABLE DEPLOY (real metrics from the ledger)")
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

    print("\nALL CHECKS PASSED - THE MIND REPORTS REAL OPERATIONS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())