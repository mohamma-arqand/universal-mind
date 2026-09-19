#!/usr/bin/env python3
"""Probe: the poison-feed bug fix and the honest-failure lens, live.

The deep-debug sweep found a REAL bug: the goal loop read payload['errors']
but the router writes payload['error'] — so every failed step recorded an
EMPTY detail, and no goal was EVER detected as poisoned. The blind retry
loop the audit predicted was invisible to the poison lens. This probe locks
the fix and the honest-failure class in the release gate:

  1. POISON-FEED: a 3x-failed step's recorded detail is NON-empty (the
     router's real error text), so _poisoned_goals() actually fires.
  2. REFUSAL: «ادامه بده» on an all-poisoned board warns instead of
     blindly re-running the broken step.
  3. HONEST-FAILURE CLASS: a no-Persian-voice speech run records
     outcome_class='blocked_env', and the predictor IGNORES such rows —
     a chain's only-"failures"-were-environmental reads strong.

Exit non-zero unless every hold is green.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_poison_feed_is_alive() -> bool:
    """A goal that fails 3x at one step must be detected as poisoned."""
    from unittest.mock import patch as mock_patch

    import universal_mind.agent_loop as am
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    with mock_patch.object(am, "_store", lambda: suite):
        started = am.start_goal("هدف: پراب زهر", ("این فرمان هیچ قابلیتی ندارد ZZZQ",))
        for _ in range(am.POISON_THRESHOLD):
            am.run_goal(started["goal_id"])
        import json

        row = suite.query("SELECT outcomes FROM goals WHERE id = ?", (str(started["goal_id"]),))
        outcomes = json.loads(row["rows"][0]["outcomes"])
        details = [o["detail"] for o in outcomes]
        poisoned = am._poisoned_goals()
        print(f"  details={details!r} | poisoned={poisoned}")
        return bool(details and all(d != "" for d in details) and started["goal_id"] in poisoned)


def check_continue_refuses_poison() -> bool:
    """«ادامه بده» with only poisoned goals → the warning, never a re-run."""
    from unittest.mock import patch as mock_patch

    import universal_mind.agent_loop as am
    import universal_mind.database_suite as ds_mod
    import universal_mind.persian_router as pr
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    with mock_patch.object(am, "_store", lambda: suite), \
         mock_patch.object(ds_mod, "DatabaseSuite", lambda persistent=False: suite):
        started = am.start_goal("هدف: پراب زهر۲", ("این فرمان هیچ قابلیتی ندارد ZZZQ",))
        for _ in range(am.POISON_THRESHOLD):
            am.run_goal(started["goal_id"])
        payload = pr.route_and_run("ادامه بده")
        report = payload.get("agent_report", "")
        print(f"  report: {report[:80]!r}")
        return "زهرآلود" in report and "اصلاح" in report


def check_blocked_env_is_not_failure() -> bool:
    """An environmental refusal records its class; the predictor ignores it."""
    from unittest.mock import patch as mock_patch

    import universal_mind.success_predictor as sp_mod
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory
    from universal_mind.success_predictor import predict_success

    suite = DatabaseSuite()
    # the predictor binds DatabaseSuite at ITS import time — patch its own name
    with mock_patch.object(sp_mod, "DatabaseSuite", lambda persistent=True: suite):
        RunHistory(suite).record("بلند بخوان", ["speech"], False, outcome_class="blocked_env")
        RunHistory(suite).record("بلند بخوان", ["speech"], True, excellence=1.0)
        RunHistory(suite).record("بلند بخوان", ["speech"], True, excellence=1.0)
        p = predict_success(("speech",))
    print(f"  prob={p.success_probability:.2f} tier={p.tier} evidence={p.evidence_runs}")
    # two real wins, zero real failures → Laplace (2+1)/(2+2) = 0.75, never dragged down
    return p.success_probability >= 0.75 and p.tier in ("strong", "medium")


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeDeepDebugHolds",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeDeepDebugHolds", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("poison-feed: failed steps record real detail, the lens fires", check_poison_feed_is_alive),
    ("refusal: «ادامه بده» warns on a poisoned board, never re-runs", check_continue_refuses_poison),
    ("honest-failure: blocked_env never poisons the predictor", check_blocked_env_is_not_failure),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Deep-debug holds probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: DEEP-DEBUG HOLDS (باگ زهر، رد صادقانه، عدالت آماری)")
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

    print("\nALL CHECKS PASSED — THE POISON LENS SEES, THE HISTORY STAYS HONEST" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())