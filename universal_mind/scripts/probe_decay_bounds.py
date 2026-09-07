#!/usr/bin/env python3
"""Probe: Verify Mnemosyne decay behavior with injected clock.

Advance clock and prove expired records removed, live records retained.
Records: FRESH (0-ttl) -> STALE (ttl-2*ttl) -> EXPIRED (2*ttl+)
"""

import argparse
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from universal_mind.core.clock import Clock
from universal_mind.core.identity import Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import CompactionPolicy, LocalJSONLStore


class InjectedClock(Clock):
    """Clock that can be advanced for testing."""
    def __init__(self, start: float = 0.0) -> None:
        self._time = start

    def now(self) -> datetime:
        return datetime.fromtimestamp(self._time, tz=timezone.utc)

    def advance(self, seconds: float) -> None:
        self._time += seconds


def run_decay_probe() -> tuple[bool, dict[str, object]]:
    """Run the decay probe with injected clock.

    Records with TTL=10:
    - FRESH: 0-10 seconds
    - STALE: 10-20 seconds
    - EXPIRED: 20+ seconds (removed by decay)
    """

    temp_dir = tempfile.mkdtemp(prefix="decay_probe_")

    try:
        clock = InjectedClock(start=1000.0)  # Start at t=1000
        # Create store with compaction policy
        compaction_policy = CompactionPolicy(
            max_tombstone_ratio=0.3,
            min_records_before_compact=10,
            max_tombstones=0
        )
        store = LocalJSONLStore(
            directory=temp_dir,
            filename="memory.jsonl",
            compaction_policy=compaction_policy
        )

        identity = Identity(owner_id="decay_user", display_name="Decay User")

        # Let's use Mnemosyne directly with decay
        mnemosyne = Mnemosyne(store, clock)

        # Add records with different TTLs
        record_ids: list[tuple[str, str, int | None]] = []

        # Record 1: TTL=10, expires at t=1020 (ttl*2)
        rec1_id = mnemosyne.record(
            owner_id=identity.owner_id,
            kind="test_record",
            payload={"text": "Record 1 - short TTL"},
            provenance={"test": "decay"},
            ttl_seconds=10,
        )
        record_ids.append(("rec1", rec1_id, 10))

        # Record 2: TTL=20, expires at t=1040 (ttl*2)
        rec2_id = mnemosyne.record(
            owner_id=identity.owner_id,
            kind="test_record",
            payload={"text": "Record 2 - medium TTL"},
            provenance={"test": "decay"},
            ttl_seconds=20,
        )
        record_ids.append(("rec2", rec2_id, 20))

        # Record 3: TTL=50, expires at t=1100 (ttl*2)
        rec3_id = mnemosyne.record(
            owner_id=identity.owner_id,
            kind="test_record",
            payload={"text": "Record 3 - long TTL"},
            provenance={"test": "decay"},
            ttl_seconds=50,
        )
        record_ids.append(("rec3", rec3_id, 50))

        # Record 4: no TTL (never expires)
        rec4_id = mnemosyne.record(
            owner_id=identity.owner_id,
            kind="test_record",
            payload={"text": "Record 4 - no TTL"},
            provenance={"test": "decay"},
            ttl_seconds=None,
        )
        record_ids.append(("rec4", rec4_id, None))

        # Check initial state
        all_records = mnemosyne.recall(owner_id=identity.owner_id)
        initial_count = len(all_records)
        print(f"Initial records: {initial_count}")

        # Advance clock to t=1015 (rec1 STALE, rec2/3/4 FRESH)
        print("Advancing clock to t=1015 (rec1 STALE, not expired)...")
        clock.advance(15)
        mnemosyne.decay()

        after_t1015 = mnemosyne.recall(owner_id=identity.owner_id)
        count_t1015 = len(after_t1015)
        print(f"Records at t=1015: {count_t1015}")

        # rec1 should still be there (STALE but not EXPIRED)
        rec1_exists = any(r.record['id'] == record_ids[0][1] for r in after_t1015)

        # Advance clock to t=1025 (rec1 EXPIRED, rec2 STALE, rec3/4 FRESH)
        print("Advancing clock to t=1025 (rec1 EXPIRED, should be removed)...")
        clock.advance(10)
        mnemosyne.decay()

        after_t1025 = mnemosyne.recall(owner_id=identity.owner_id)
        count_t1025 = len(after_t1025)
        print(f"Records at t=1025: {count_t1025}")

        rec2_exists = any(r.record['id'] == record_ids[1][1] for r in after_t1025)
        rec1_still_exists = any(r.record['id'] == record_ids[0][1] for r in after_t1025)

        # Advance clock to t=1060 (rec1/2 EXPIRED, rec3 STALE, rec4 FRESH)
        print("Advancing clock to t=1060 (rec1/2 EXPIRED, rec3 STALE)...")
        clock.advance(35)
        mnemosyne.decay()

        after_t1060 = mnemosyne.recall(owner_id=identity.owner_id)
        count_t1060 = len(after_t1060)
        print(f"Records at t=1060: {count_t1060}")

        rec3_exists = any(r.record['id'] == record_ids[2][1] for r in after_t1060)
        rec4_exists = any(r.record['id'] == record_ids[3][1] for r in after_t1060)

        # Final advance to t=1110 (all with TTL expired)
        print("Advancing clock to t=1110 (rec3 EXPIRED)...")
        clock.advance(50)
        mnemosyne.decay()

        after_t1110 = mnemosyne.recall(owner_id=identity.owner_id)
        count_t1110 = len(after_t1110)
        print(f"Records at t=1110: {count_t1110}")

        rec3_still_exists = any(r.record['id'] == record_ids[2][1] for r in after_t1110)
        rec4_final_exists = any(r.record['id'] == record_ids[3][1] for r in after_t1110)

        # Final verification
        # Check actual states
        print("\nFinal check:")
        print(f"  rec1 at t=1015 (should be STALE, exist): {rec1_exists}")
        print(f"  rec1 at t=1025 (should be EXPIRED, removed): {rec1_still_exists}")
        print(f"  rec2 at t=1025 (should be STALE, exist): {rec2_exists}")
        print(f"  rec3 at t=1060 (should be STALE, exist): {rec3_exists}")
        print(f"  rec3 at t=1110 (should be EXPIRED, removed): {rec3_still_exists}")
        print(f"  rec4 at t=1060 (should be FRESH, exist): {rec4_exists}")
        print(f"  rec4 at t=1110 (should be FRESH, exist): {rec4_final_exists}")

        success = (
            rec1_exists and              # rec1 STALE at t=1015
            not rec1_still_exists and    # rec1 EXPIRED and removed at t=1025
            rec2_exists and              # rec2 STALE at t=1025
            rec3_exists and              # rec3 STALE at t=1060
            not rec3_still_exists and    # rec3 EXPIRED and removed at t=1110
            rec4_exists and              # rec4 FRESH at t=1060
            rec4_final_exists            # rec4 FRESH at t=1110
        )

        result: dict[str, object] = {
            "initial_records": initial_count,
            "records_at_t1015": count_t1015,
            "records_at_t1025": count_t1025,
            "records_at_t1060": count_t1060,
            "records_at_t1110": count_t1110,
            "rec1_at_t1015_STALE": rec1_exists,
            "rec1_at_t1025_EXPIRED_REMOVED": not rec1_still_exists,
            "rec2_at_t1025_STALE": rec2_exists,
            "rec3_at_t1060_STALE": rec3_exists,
            "rec3_at_t1110_EXPIRED_REMOVED": not rec3_still_exists,
            "rec4_at_t1060_FRESH": rec4_exists,
            "rec4_at_t1110_FRESH": rec4_final_exists,
        }

        return success, result

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_junit_xml(passed: bool, output_file: str) -> None:
    """Write test results to JUnit XML format."""
    testsuite = ET.Element("testsuite", {
        "name": "ProbeDecayBounds",
        "tests": "1",
        "failures": "0" if passed else "1",
        "errors": "0",
        "time": "0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    })

    testcase = ET.SubElement(testsuite, "testcase", {
        "name": "decay_bounds_test",
        "classname": "ProbeDecayBounds",
        "time": "0"
    })
    if not passed:
        ET.SubElement(testcase, "failure", {
            "message": "Decay bounds test failed",
            "type": "AssertionError"
        })

    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mnemosyne Decay Bounds Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: Mnemosyne Decay with Injected Clock")
    print("=" * 60)

    print("\n--- Decay Test ---")
    passed, result = run_decay_probe()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k}: {v}")

    if args.junit_xml:
        write_junit_xml(passed, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if passed:
        print("\nALL CHECKS PASSED - DECAY WORKS CORRECTLY")
        return 0
    else:
        print("\nSOME CHECKS FAILED - DECAY NOT WORKING")
        return 1


if __name__ == "__main__":
    sys.exit(main())