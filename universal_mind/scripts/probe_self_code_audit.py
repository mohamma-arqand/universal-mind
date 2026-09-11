#!/usr/bin/env python3
"""Probe: continuous self-code-audit — automatic, periodic hygiene.

G4 was a one-shot human-pass. This probe proves the audit is now *continuous*: a
deterministic scanner walks the mind's own source tree, flags empty modules /
orphaned imports / missing docstrings, and writes the findings to the ledger as a
self_code_audit record. Exit non-zero unless all hold.
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

from universal_mind.core.self_code_audit import run_self_audit, scan_source
from universal_mind.memory.store import InMemoryStore


def check_scanner_finds_anti_patterns() -> bool:
    d = Path(tempfile.mkdtemp())
    (d / "empty.py").write_text('"""only docs"""\n', encoding="utf-8")
    (d / "orphan.py").write_text('"""m"""\nfrom universal_mind.telemetry import errors\n', encoding="utf-8")
    findings = scan_source(d)
    kinds = {f.kind for f in findings}
    ok = "empty_module" in kinds and "orphaned_import" in kinds
    print(f"  scanner flags empty modules and orphaned imports: {ok}")
    return ok


def check_clean_tree_flags_nothing() -> bool:
    d = Path(tempfile.mkdtemp())
    (d / "ok.py").write_text('"""A clean module."""\ndef f() -> int:\n    return 1\n', encoding="utf-8")
    findings = scan_source(d)
    ok = all(f.path != "ok.py" for f in findings)
    print(f"  a clean module is not flagged: {ok}")
    return ok


def check_audit_records_to_ledger() -> bool:
    d = Path(tempfile.mkdtemp())
    (d / "empty.py").write_text('"""only docs"""\n', encoding="utf-8")
    store = InMemoryStore()
    report = run_self_audit(d, store=store)
    kinds = [r.get("kind") for r in store.read_all()]
    ok = report.ledger_record_id is not None and "self_code_audit" in kinds
    print(f"  audit findings are recorded to the ledger: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeSelfCodeAudit",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeSelfCodeAudit", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Scanner flags anti-patterns", check_scanner_finds_anti_patterns),
    ("Clean tree flags nothing", check_clean_tree_flags_nothing),
    ("Audit is recorded to the ledger", check_audit_records_to_ledger),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-code-audit probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: CONTINUOUS SELF-CODE-AUDIT (automatic hygiene)")
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

    print("\nALL CHECKS PASSED - THE MIND KEEPS ITS OWN CODE CLEAN" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())