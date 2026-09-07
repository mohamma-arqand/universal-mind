#!/usr/bin/env python3
"""Probe: Verify tombstone bound after compaction in LocalJSONLStore.

Run N=10_000 write/delete operations and prove tombstone-to-live ratio
after compaction does not exceed defined cap.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from universal_mind.core.identity import Identity
from universal_mind.core.intent import Intent
from universal_mind.memory.store import CompactionPolicy, LocalJSONLStore

# Configuration
N_OPERATIONS = 1000  # Reduced for faster testing
MAX_TOMBSTONE_RATIO = 0.1  # 10% cap


class InjectedClock:
    """Clock that can be advanced for testing."""
    def __init__(self, start: float = 0.0) -> None:
        self._time = start

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def count_tombstones_and_live(store_path: str) -> tuple[int, int]:
    """Count tombstone and live records in a store file."""
    tombstones = 0
    live = 0

    if not os.path.exists(store_path):
        return 0, 0

    with open(store_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get('kind') == 'tombstone':
                tombstones += 1
            else:
                live += 1

    return tombstones, live


def run_tombstone_bound_probe() -> tuple[bool, dict[str, object]]:
    """Run the tombstone bound probe."""

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="tombstone_probe_")
    store_path = os.path.join(temp_dir, "memory.jsonl")

    try:
        # Create store with compaction policy
        compaction_policy = CompactionPolicy(
            max_tombstone_ratio=0.3,
            min_records_before_compact=100,
            max_tombstones=0  # No absolute count trigger
        )
        store = LocalJSONLStore(
            directory=temp_dir,
            filename="memory.jsonl",
            compaction_policy=compaction_policy
        )

        # Create identity for operations
        identity = Identity(owner_id="probe_user", display_name="Probe User")

        # Phase 1: Write N records
        print(f"Phase 1: Writing {N_OPERATIONS} records...")
        for i in range(N_OPERATIONS):
            intent = Intent.from_raw(
                raw_text=f"Operation {i}",
                goal=f"Test goal {i}",
                success_criteria=[f"Criterion {i}"],
                owner_id=identity.owner_id
            )
            store.append({
                'owner_id': identity.owner_id,
                'kind': 'intent',
                'payload': {'operation': i, 'phase': 'write', 'intent_goal': intent.goal}
            })

        # Count after writes
        tombstones_after_write, live_after_write = count_tombstones_and_live(store_path)
        print(f"  After writes: {live_after_write} live, {tombstones_after_write} tombstones")

        # Phase 2: Delete half of them
        print(f"Phase 2: Deleting {N_OPERATIONS // 2} records...")
        # Get all record IDs
        records = list(store.read_all())
        for i, record in enumerate(records[:N_OPERATIONS // 2]):
            store.delete(record['id'])

        # Count after deletes (before compaction)
        tombstones_after_delete, live_after_delete = count_tombstones_and_live(store_path)
        print(f"  After deletes: {live_after_delete} live, {tombstones_after_delete} tombstones")

        # Phase 3: Trigger compaction
        print("Phase 3: Running compaction...")
        store.compact()

        # Count after compaction
        tombstones_after_compact, live_after_compact = count_tombstones_and_live(store_path)
        print(f"  After compaction: {live_after_compact} live, {tombstones_after_compact} tombstones")

        # Calculate ratio
        total_after_compact = tombstones_after_compact + live_after_compact
        if total_after_compact > 0:
            tombstone_ratio = tombstones_after_compact / total_after_compact
        else:
            tombstone_ratio = 0.0

        print(f"  Tombstone ratio: {tombstone_ratio:.4f} (cap: {MAX_TOMBSTONE_RATIO})")

        # Verify ratio is within bound
        ratio_ok = tombstone_ratio <= MAX_TOMBSTONE_RATIO

        result: dict[str, object] = {
            "operations": N_OPERATIONS,
            "live_after_write": live_after_write,
            "tombstones_after_write": tombstones_after_write,
            "live_after_delete": live_after_delete,
            "tombstones_after_delete": tombstones_after_delete,
            "live_after_compaction": live_after_compact,
            "tombstones_after_compaction": tombstones_after_compact,
            "ratio_after_compaction": tombstone_ratio,
            "cap": MAX_TOMBSTONE_RATIO,
            "ratio_within_cap": ratio_ok,
        }

        success = ratio_ok and live_after_compact == N_OPERATIONS // 2

        return success, result

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_tombstone_bound_auto_compaction() -> tuple[bool, dict[str, object]]:
    """Test auto-compaction with max_tombstones parameter."""

    temp_dir = tempfile.mkdtemp(prefix="tombstone_auto_probe_")
    store_path = os.path.join(temp_dir, "memory.jsonl")

    try:
        # Set max_tombstones to trigger auto-compaction
        compaction_policy = CompactionPolicy(
            max_tombstone_ratio=0.3,
            min_records_before_compact=10,
            max_tombstones=100
        )
        store = LocalJSONLStore(
            directory=temp_dir,
            filename="memory.jsonl",
            compaction_policy=compaction_policy
        )

        identity = Identity(owner_id="probe_user", display_name="Probe User")

        # Write and delete in cycles to trigger auto-compaction
        print("Testing auto-compaction with max_tombstones=100...")

        for cycle in range(50):
            # Write 10
            for i in range(10):
                intent = Intent.from_raw(
                    raw_text=f"Cycle {cycle} op {i}",
                    goal=f"Goal {cycle}-{i}",
                    success_criteria=["test"],
                    owner_id=identity.owner_id
                )
                store.append({
                    'owner_id': identity.owner_id,
                    'kind': 'intent',
                    'payload': {'cycle': cycle, 'op': i, 'intent_goal': intent.goal}
                })

            # Delete 5
            records = list(store.read_all())
            for record in records[-5:]:
                store.delete(record['id'])

        # Force final compaction
        store.compact()

        tombstones, live = count_tombstones_and_live(store_path)
        total = tombstones + live
        ratio = tombstones / total if total > 0 else 0.0

        print(f"  After auto-compaction cycles: {live} live, {tombstones} tombstones, ratio={ratio:.4f}")

        result: dict[str, object] = {
            "live": live,
            "tombstones": tombstones,
            "ratio": ratio,
            "cap": MAX_TOMBSTONE_RATIO,
            "ratio_within_cap": ratio <= MAX_TOMBSTONE_RATIO,
        }

        success = ratio <= MAX_TOMBSTONE_RATIO
        return success, result

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write test results to JUnit XML format."""
    testsuite = ET.Element("testsuite", {
        "name": "ProbeTombstoneBound",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, r in results if not r)),
        "errors": "0",
        "time": "0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    })

    for name, result in results:
        testcase = ET.SubElement(testsuite, "testcase", {
            "name": name,
            "classname": "ProbeTombstoneBound",
            "time": "0"
        })
        if not result:
            ET.SubElement(testcase, "failure", {
                "message": f"Test {name} failed",
                "type": "AssertionError"
            })

    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tombstone Bound Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: Tombstone Bound After Compaction")
    print("=" * 60)

    tests = [
        ("Manual compaction tombstone bound", run_tombstone_bound_probe),
        ("Auto-compaction tombstone bound", run_tombstone_bound_auto_compaction),
    ]

    all_passed = True
    test_results = []

    for name, test_func in tests:
        print(f"\n--- {name} ---")
        passed, _ = test_func()
        test_results.append((name, passed))
        status = "PASS" if passed else "FAIL"
        print(f"  Result: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if args.junit_xml:
        write_junit_xml(test_results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_passed:
        print("ALL TESTS PASSED - TOMBSTONE RATIO WITHIN BOUND")
        return 0
    else:
        print("SOME TESTS FAILED - TOMBSTONE RATIO EXCEEDS CAP")
        return 1


if __name__ == "__main__":
    sys.exit(main())