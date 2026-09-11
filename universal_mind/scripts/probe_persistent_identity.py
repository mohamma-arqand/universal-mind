#!/usr/bin/env python3
"""Probe: persistent identity — continuous identity survives a restart.

A fresh identity per session means the mind forgets who it is between runs. This
probe proves the continuity layer: an identity persisted to the ledger is
recovered as the SAME owner on a fresh recover (a restart), and a default is used
when no prior identity exists. Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.core.identity import Identity
from universal_mind.core.persistent_identity import persist_identity, recover_identity
from universal_mind.memory.store import InMemoryStore


def check_identity_survives_restart() -> bool:
    store = InMemoryStore()
    persist_identity(store, Identity("alice", "Alice"))
    handle = recover_identity(store)  # a "restart"
    ok = handle.recovered is True and handle.identity.owner_id == "alice"
    print(f"  persisted identity is recovered after restart: {ok}")
    return ok


def check_default_when_no_prior_identity() -> bool:
    store = InMemoryStore()
    handle = recover_identity(store)
    ok = handle.recovered is False and handle.identity.owner_id == "sovereign"
    print(f"  a default identity is used when none is persisted: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbePersistentIdentity",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbePersistentIdentity", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Identity survives a restart", check_identity_survives_restart),
    ("Default when no prior identity", check_default_when_no_prior_identity),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Persistent identity probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: PERSISTENT IDENTITY (the same owner across sessions)")
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

    print("\nALL CHECKS PASSED - THE MIND REMEMBERS WHO IT IS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())