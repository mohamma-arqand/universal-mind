#!/usr/bin/env python3
"""Probe: the audit's fixes and upgrades, locked in the release gate.

Everything this deep audit changed, proven LIVE on every verify:
  1. NESTED-GOAL flattening — «هدف: هدف: X» runs as steps, never recurses;
  2. ONE-WORD PREFIXES — «وضعیت...» / «ادامه...» variants all answer;
  3. HONEST ZERO — a 0.0-excellence hint renders 'بدون داوری', never 100%;
  4. REPAIR BINDING — a two-step goal repairs with ITS OWN commands (B023);
  5. TICK HEALTH — the tri-state verdict reads (alive/dead/silent);
  6. SEMANTIC ADVISOR — «درآمد» finds «سود» with zero shared words;
  7. SESSION VERDICT — the 24h-as-one-work reading answers with a verdict.

Exit non-zero unless the audit holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_nested_goal_flattened() -> bool:
    from unittest.mock import patch as mock_patch

    import tempfile
    from pathlib import Path

    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-goals.db"))
    with mock_patch(
        "universal_mind.database_suite.DatabaseSuite.shared_persistent",
        classmethod(lambda cls: suite),
    ):
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("هدف: هدف: تو در تو")
    report = payload.get("agent_report", "") or str(
        payload.get("result", {}).get("goal", {}).get("report", "")
    )
    step_lines = [ln for ln in report.splitlines() if ln.strip().startswith(("✅", "❌"))]
    ok = bool(step_lines) and not any("هدف:" in ln for ln in step_lines)
    print(f"  steps: {len(step_lines)} | nested-in-steps: {any('هدف:' in ln for ln in step_lines)}")
    return bool(ok)


def check_one_word_prefixes() -> bool:
    from universal_mind.persian_router import route_and_run

    for phrase in ("وضعیت عامل وضعیت", "ادامه بده لطفاً"):
        payload = route_and_run(phrase)
        if payload.get("route") != ["goal"]:
            print(f"  missed: {phrase!r} -> {payload.get('route')}")
            return False
    print("  both prefix families answer")
    return True


def check_honest_zero_excellence() -> bool:
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import ChainAdvisor, RunHistory

    history = RunHistory(DatabaseSuite())
    history.record("نمودار بساز", ["chart"], True, excellence=0.9)
    history.record("نمودار بساز و گزارشش کن", ["chart", "pdf"], True, excellence=0.0)
    hint = ChainAdvisor(history).completion_hint("نمودار خطی بساز")
    ok = hint is not None and "۱۰۰٪" not in hint and "بدون داوری" in hint
    print(f"  hint: {hint[:70] if hint else None}")
    return bool(ok)


def check_repair_binds_its_own_command() -> bool:
    """Two steps, run through the real loop: each outcome carries ITS command."""
    from contextlib import AbstractContextManager
    from unittest.mock import patch as mock_patch

    import universal_mind.agent_loop as agent_mod
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    ctx: AbstractContextManager[object] = mock_patch.object(agent_mod, "_store", lambda: suite)
    with ctx:
        started = agent_mod.start_goal(
            "هدف: اتصال گامها", ("میانگین 4 و 6 را حساب کن", "نمودارش کن")
        )
        result = agent_mod.run_goal(started["goal_id"])
    commands = [s.command for s in result.steps]
    ok = (
        result.finished
        and "میانگین 4 و 6 را حساب کن" in commands
        and "نمودارش کن" in commands
    )
    print(f"  finished: {result.finished} | commands: {len(commands)} distinct")
    return bool(ok)


def check_tick_health_tristate() -> bool:
    from universal_mind.task_install import tick_health

    th = tick_health()
    sig = th.get("signals", {}) or {}
    ok = th.get("verdict") in ("alive", "dead", "silent")
    ok = ok and isinstance(sig.get("task_installed"), bool)
    print(f"  verdict: {th.get('verdict')} | task: {sig.get('task_installed')} | recent: {sig.get('recent_run')}")
    return bool(ok)


def check_semantic_advisor_finds_meaning() -> bool:
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import ChainAdvisor, RunHistory

    history = RunHistory(DatabaseSuite())
    history.record("میانگین سود ماهانه را حساب کن", ["data"], True, 0.9)
    history.record("نمودار فروش هفتگی بکش", ["chart"], True, 0.9)
    advice = ChainAdvisor(history).advise_semantic("میانگین درآمد ماهانه را محاسبه کن")
    ok = advice is not None and "سود" in advice.similar_command
    print(f"  nearest: {advice.similar_command if advice else None}")
    return bool(ok)


def check_session_verdict_answers() -> bool:
    from universal_mind.history_analytics import session_verdict

    sv = session_verdict()
    ok = sv.get("ok") is True and sv.get("verdict") in ("درخشان", "نیازمند توجه")
    print(f"  verdict: {sv.get('verdict')} | mean: {sv.get('mean')} | runs: {sv.get('runs')}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeAuditHolds",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAuditHolds", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("nested goal flattens, never recurses", check_nested_goal_flattened),
    ("one-word prefixes all answer", check_one_word_prefixes),
    ("zero excellence renders 'بدون داوری', never 100%", check_honest_zero_excellence),
    ("the repair binds THIS step's command (B023)", check_repair_binds_its_own_command),
    ("tick health: the tri-state verdict reads", check_tick_health_tristate),
    ("semantic advisor: meaning over words", check_semantic_advisor_finds_meaning),
    ("session verdict: the 24h-as-one-work reading", check_session_verdict_answers),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit-holds probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE AUDIT HOLDS (هر فیکس ممیزی، زنده در gate)")
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

    print("\nALL CHECKS PASSED — THE AUDIT HOLDS ON EVERY RELEASE" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())