#!/usr/bin/env python3
"""Probe: durable local persistence — the ledger survives restart/reopen.

Runs the composed system against a LocalJSONLStore on disk, then proves the
ledger is durable: it reloads in-process on reopen, it survives a brand-new
Python process, and a fault recorded during a failed execution is still present
after reopen (recovery). Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

from universal_mind.durable import PersistentMind
from universal_mind.integration import (
    InMemoryIntegrationHarness,
    IntegrationError,
)
from universal_mind.io.errors import ProviderPermanent
from universal_mind.io.gateway import Gateway, ScriptedProvider
from universal_mind.memory.store import LocalJSONLStore


def attempt_ledger_persists() -> bool:
    """A run leaves a non-empty JSONL ledger on disk."""
    with tempfile.TemporaryDirectory() as td:
        mind = PersistentMind.open(td)
        mind.run("summarize", "persist me")
        ledger = os.path.join(td, "ledger.jsonl")
        ok = os.path.exists(ledger) and os.path.getsize(ledger) > 0 and mind.ledger_size > 0
        print(f"  ledger persistent on disk: {ok} (records={mind.ledger_size})")
        return ok


def attempt_reopen_reloads() -> bool:
    """Reopening the same directory reloads the same ledger."""
    with tempfile.TemporaryDirectory() as td:
        first = PersistentMind.open(td)
        first.run("summarize", "hello")
        second = PersistentMind.reopen(td)
        ok = second.ledger_size == first.ledger_size and second.ledger_kinds() == first.ledger_kinds()
        print(f"  reloaded records={second.ledger_size} kinds={second.ledger_kinds()} same={ok}")
        return ok


def attempt_cross_process_durability() -> bool:
    """A brand-new Python process sees the same ledger from disk."""
    with tempfile.TemporaryDirectory() as td:
        mind = PersistentMind.open(td)
        mind.run("summarize", "across processes")
        n = mind.ledger_size
        child = (
            "import os\n"
            "from universal_mind.durable import PersistentMind\n"
            "m = PersistentMind.reopen(os.environ['UM_DURABLE_DIR'])\n"
            "print('LEDGER', m.ledger_size)\n"
        )
        env = dict(os.environ, PYTHONPATH=_REPO_ROOT, UM_DURABLE_DIR=td)
        result = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, env=env, timeout=60, check=False)
        ok = result.returncode == 0 and f"LEDGER {n}" in result.stdout
        print(f"  process1 wrote {n}; process2 read={ok} ({result.stdout.strip()!r})")
        return ok


def attempt_recovery_sees_fault() -> bool:
    """A fault recorded on disk is still readable after reopen (recovery)."""
    with tempfile.TemporaryDirectory() as td:
        store = LocalJSONLStore(directory=td)
        h1 = InMemoryIntegrationHarness(Gateway([ScriptedProvider([ProviderPermanent("down")])]), store=store)
        try:
            h1.run("summarize", "will fail")
            failed_to_raise = True
        except IntegrationError:
            failed_to_raise = False
        kinds = {r.get("kind") for r in LocalJSONLStore(directory=td).read_all()}
        ok = (not failed_to_raise) and ("fault" in kinds) and ("capability_result" not in kinds)
        print(f"  fault recorded on disk: {'fault' in kinds} (raised={not failed_to_raise})")
        return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeDurability",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeDurability", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Ledger is persistently written to disk", attempt_ledger_persists),
    ("Reopen reloads the same ledger", attempt_reopen_reloads),
    ("Ledger survives a fresh process (durability)", attempt_cross_process_durability),
    ("Recovery reads a recorded fault after reopen", attempt_recovery_sees_fault),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="Durable Persistence Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: DURABLE LOCAL PERSISTENCE (LocalJSONLStore)")
    print("=" * 60)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        results.append((name, fn()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_ok = True
    for name, result in results:
        status = "OK" if result else "FAILED"
        print(f"  {name}: {status}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - THE LOCAL LEDGER IS DURABLE AND SURVIVES RESTART/REOPEN")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())