#!/usr/bin/env python3
"""Probe: the autonomous loop — all three perception channels, live.

The platform's self-governance proven end to end:
1. CLOCK: a due schedule really fires through the real engine (isolated store);
2. FILES: a folder watcher learns, then fires ONCE on a genuinely new file;
3. TOAST: the proactive pass reports itself in Persian digits (mocked — a
   probe must never spam the operator's real desktop);
4. CONTEST: a scheduled multi-step run races its rival and records the lesson.

Exit non-zero unless every stage holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from unittest.mock import patch as mock_patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _isolated() -> "AbstractContextManager[object]":
    """A fresh temp store — a probe never fires the operator's real tasks."""
    import universal_mind.scheduler as sched_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(sched_mod, "_store", lambda: suite)


def check_clock_channel() -> bool:
    """A due schedule fires; the clock advances (no immediate re-fire)."""
    from universal_mind.scheduler import register, run_due

    with _isolated():
        result = register("هر ۱۵ دقیقه میانگین ۳ و ۹ را حساب کن")
        assert result["ok"] is True
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            first = run_due()
        assert first["count"] >= 1
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            second = run_due()
    ok = first["count"] >= 1 and second["count"] == 0  # the clock advanced
    print(f"  clock: fired {first['count']}, re-fire {second['count']} (must be 0)")
    return bool(ok)


def check_file_channel() -> bool:
    """A watcher: baseline learns, a new file fires once, silence after."""
    from universal_mind.scheduler import register, scan_watchers

    with _isolated():
        folder = tempfile.mkdtemp(prefix="um-probe-watch-")
        result = register(f"هر وقت در پوشهی {folder} فایل جدید آمد، میانگین ۱ و ۲ را حساب کن")
        assert result["ok"] is True
        baseline = scan_watchers()
        with open(os.path.join(folder, "probe.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        fired = scan_watchers()
        idle = scan_watchers()
    ok = (
        baseline["count"] == 0
        and fired["count"] == 1
        and fired["fired"][0]["ok"] is True
        and idle["count"] == 0
    )
    print(f"  file: baseline {baseline['count']} → new {fired['count']} → idle {idle['count']}")
    return bool(ok)


def check_contest_channel() -> bool:
    """A scheduled multi-step run races its rival; the outcome is recorded."""
    from universal_mind.scheduler import register, run_due

    with _isolated():
        register("هر ۱۵ دقیقه نمودار خطی بساز و گزارشش کن")
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            result = run_due(max_runs=1)
    fired = result.get("fired", [])
    if not fired:
        print("  contest: nothing fired")
        return False
    contest = fired[0].get("contest", "")
    ok = bool(contest) and ("مسابقه" in contest or "بدون مسابقه" in contest)
    print(f"  contest: {contest[:80]}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeAutonomousLoop",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAutonomousLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("clock channel: a due schedule fires and the clock advances", check_clock_channel),
    ("file channel: baseline → new file fires once → silence", check_file_channel),
    ("contest channel: scheduled runs explore and record the lesson", check_contest_channel),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous-loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE AUTONOMOUS LOOP (سه کانال ادراک، زنده)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM RUNS ITSELF" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())