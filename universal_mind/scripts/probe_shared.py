#!/usr/bin/env python3
"""Probe: distributed memory — several instances over one synchronized ledger.

A single-process mind forgets when the process dies and cannot see another mind's
experience. This probe proves the shared-ledger layer: multiple store handles over
the same on-disk JSONL file are synchronized — a write through one is immediately
visible through the others. Exit non-zero unless all hold.
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

from universal_mind.memory.shared import (
    append_through,
    is_synchronized,
    open_shared_ledger,
)


def check_write_through_one_visible_to_other() -> bool:
    d = tempfile.mkdtemp()
    a, b = open_shared_ledger(d)
    append_through(a, "alice", "note", {"x": 1})
    ok = is_synchronized([a, b]) is True and len(list(b.read_all())) == 1
    print(f"  a write through one instance is visible to the other: {ok}")
    return ok


def check_three_instances_converge() -> bool:
    d = tempfile.mkdtemp()
    handles = open_shared_ledger(d, instances=3)
    append_through(handles[0], "alice", "n1", {})
    append_through(handles[1], "bob", "n2", {})
    ok = is_synchronized(handles) is True and len(list(handles[2].read_all())) == 2
    print(f"  three instances converge on one shared memory: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeDistributedMemory",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeDistributedMemory", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Write through one is visible to the other", check_write_through_one_visible_to_other),
    ("Three instances converge", check_three_instances_converge),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Distributed memory probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: DISTRIBUTED MEMORY (several instances, one synchronized ledger)")
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

    print("\nALL CHECKS PASSED - THE MIND SHARES ONE MEMORY" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())