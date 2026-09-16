#!/usr/bin/env python3
"""Probe: the planning + quality-gate loop — judgment that changes behavior.

The two deepest additions to the Persian loop, proven live:
1. THE PLANNER: word order no longer dictates execution order. «گزارشش کن و
   نمودار بساز» (said backwards) still runs chart → pdf because the plan is
   derived from what each operation NEEDS, and the pdf genuinely embeds the
   chart (bytes grow) — synthesis, not two disconnected artifacts.
2. THE QUALITY GATE: every run is ARETĒ-judged; a weak verdict (below the bar)
   triggers real self-repair through the honest rival route, and only the best
   REAL verdict ships. The gate is one level deep (a gate candidate never
   re-enters the gate) and never hides a failed attempt.
3. THE OP WORDS: a sentence can now NAME the document kind (فاکتور → invoice,
   نامه → letterhead, جدول → styled_table) and the explicit choice always wins
   over inference.

Exit non-zero unless every stage holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_planner_beats_word_order() -> bool:
    """Backwards words → correct order → real synthesis."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("گزارشش کن و نمودار خطی بساز")
    ok = payload["ok"] is True
    ok = ok and payload["route"] == ["chart", "pdf"]
    ok = ok and any("نمودار درونش" in f for f in payload.get("flows", []))
    pdf = payload.get("result", {}).get("pdf", {})
    ok = ok and pdf.get("bytes", 0) > 20000  # the chart is really inside
    print(f"  route: {payload['route']} | pdf bytes: {pdf.get('bytes')}")
    return bool(ok)


def check_planner_in_pure_form() -> bool:
    """The planner's own contract, in isolation: consumers after producers."""
    from universal_mind.dependency_planner import plan_chain

    plan = plan_chain(["pdf", "chart", "data"])
    caps = [s.capability for s in plan.steps]
    ok = caps.index("data") < caps.index("chart") < caps.index("pdf")
    # and pdf picked the operation that embeds (synthesis-aware choice)
    pdf_step = [s for s in plan.steps if s.capability == "pdf"][0]
    ok = ok and pdf_step.operation == "persian_report"
    print(f"  plan: {[(s.capability, s.operation) for s in plan.steps]}")
    return bool(ok)


def check_op_words_name_real_documents() -> bool:
    """فاکتور really produces an invoice, نامه a letterhead — explicit wins."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("فاکتور بساز و نمودار خطی بساز")
    op = payload.get("extracted_params", {}).get("pdf", {}).get("operation")
    ok = payload["ok"] is True and op == "invoice"
    print(f"  invoice op: {op} | ok: {payload['ok']}")
    return bool(ok)


def check_quality_gate_self_repairs() -> bool:
    """A weak primary triggers the rival; the best REAL verdict ships."""
    from typing import Any

    from universal_mind.quality_gate import run_with_quality_gate

    def runner(route: tuple[str, ...]) -> dict[str, Any]:
        # only the producer-first order yields a real image-bearing report
        good = route == ("chart", "pdf")
        if good:
            return {
                "ok": True, "command": "x", "route": list(route),
                "result": {"chart": {"path": "c.png", "bytes": 25000},
                           "pdf": {"path": "r.pdf", "bytes": 61847}},
                "errors": {}, "durations_ms": {"chart": 10.0, "pdf": 12.0},
            }
        return {
            "ok": False, "command": "x", "route": list(route),
            "result": {},
            "errors": {"pdf": "نموداری برای درج نیست"},
            "durations_ms": {"pdf": 1.0},
        }

    outcome = run_with_quality_gate("x", ("pdf", "chart"), runner, bar=0.7)
    ok = outcome.repaired is True and outcome.shipped.route == ("chart", "pdf")
    ok = ok and outcome.attempts[0].route == ("pdf", "chart")  # primary kept for audit
    print(f"  repaired: {outcome.repaired} | shipped: {outcome.shipped.route} | {outcome.reasoning[:60]}")
    return bool(ok)


def check_gate_never_double_runs_excellent_work() -> bool:
    """Excellence ≥ bar on the first run → exactly ONE execution."""
    calls: list[tuple[str, ...]] = []

    def runner(route: tuple[str, ...]) -> dict[str, object]:
        calls.append(route)
        return {
            "ok": True, "command": "x", "route": list(route),
            "result": {"data": {"mean": 3.0}},
            "errors": {}, "durations_ms": {"data": 1.0},
        }

    from universal_mind.quality_gate import run_with_quality_gate

    outcome = run_with_quality_gate("x", ("data",), runner, bar=0.5)
    ok = outcome.repaired is False and len(calls) == 1
    print(f"  runs: {len(calls)} | repaired: {outcome.repaired}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbePlanningGate",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbePlanningGate", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("planner: backwards words get the right order (real synthesis)", check_planner_beats_word_order),
    ("planner: pure form — producers before consumers + synthesis-aware op", check_planner_in_pure_form),
    ("op words: فاکتور really names the invoice operation", check_op_words_name_real_documents),
    ("quality gate: weak primary self-repairs through the rival", check_quality_gate_self_repairs),
    ("quality gate: excellent work is never double-run", check_gate_never_double_runs_excellent_work),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Planning + quality-gate probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: PLANNING + QUALITY GATE (برنامهریز + دروازهی کیفیت)")
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

    print("\nALL CHECKS PASSED — JUDGMENT CHANGES BEHAVIOR" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())