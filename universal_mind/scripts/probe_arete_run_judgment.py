#!/usr/bin/env python3
"""Probe: ARETĒ judges the platform's own real work (the closed judgment loop).

The charter's deepest axiom — judgment is not a scoreboard, it inspects real
work — finally reaches the super-platform's own runs. This probe proves the full
loop live: a real Persian command runs real programs, the dataflow fuses their
outputs (chart → pdf embeds the real chart), ARETĒ virtue-judges the run from
its own data, the verdict is recorded to the persistent history, and the
analytics surface reports the mean excellence.

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


def check_dataflow_chart_feeds_pdf() -> bool:
    """One program's real output becomes the next program's input."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("نمودار خطی از ۲ و ۵ و ۹ بساز و گزارشش کن")
    ok = payload["ok"] is True
    ok = ok and payload["flows"] == ["chart → pdf (گزارش فارسی با نمودار درونش)"]
    pdf = payload["result"].get("pdf", {})
    ok = ok and pdf.get("bytes", 0) > 20000  # the chart image is really inside
    print(f"  flows: {payload['flows']} | pdf bytes: {pdf.get('bytes')}")
    return bool(ok)


def check_arete_judges_the_real_run() -> bool:
    """The four virtues are computed from the run's own data."""
    from universal_mind.persian_router import route_and_run

    payload = route_and_run("میانگین ۲ و ۴ و ۶ را حساب کن و نمودار از ۲ و ۵ و ۹ کن")
    judgment = payload.get("judgment") or {}
    scores = judgment.get("scores", {})
    print(f"  excellence: {judgment.get('excellence')} | scores: {scores}")
    return bool(
        judgment
        and judgment.get("excellence", 0.0) >= 0.9
        and abs(scores.get("wisdom", 0.0) - 1.0) < 1e-9
        and abs(scores.get("justice", 0.0) - 1.0) < 1e-9
        and judgment.get("disqualified") is False
    )


def check_report_narrates_judgment() -> bool:
    """The fluent Persian report carries the ARETĒ line."""
    from universal_mind.persian_report import persian_report
    from universal_mind.persian_router import route_and_run

    report = persian_report(route_and_run("نمودار خطی از ۲ و ۵ و ۹ بساز و گزارشش کن"))
    ok = "🏛" in report and "داوری ARETĒ" in report and "🔗" in report
    first_lines = " / ".join(report.splitlines()[:3])
    print(f"  report: {first_lines[:100]}")
    return bool(ok)


def check_history_carries_excellence() -> bool:
    """The verdict is durable: the persistent history stores excellence."""
    from universal_mind.run_history import RunHistory

    history = RunHistory()
    q = history._db.query(
        "SELECT excellence FROM run_history WHERE succeeded = 1 "
        "AND excellence IS NOT NULL ORDER BY id DESC LIMIT 1"
    )
    if not q.get("ok") or not q.get("rows"):
        print("  (no excellence recorded yet)")
        return False
    value = float(q["rows"][0]["excellence"])
    print(f"  newest recorded excellence: {value}")
    return value > 0.0


def check_analytics_report_mean_excellence() -> bool:
    """The analytics tab shows ARETĒ's mean over judged runs."""
    from universal_mind.history_analytics import analytics_report, analyze_history

    stats = analyze_history()
    report = analytics_report(stats)
    has = stats.mean_excellence > 0.0 and "میانگین داوری ARETĒ" in report
    print(f"  total: {stats.total_runs} | mean excellence: {stats.mean_excellence}")
    return bool(has)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeAreteRunJudgment",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeAreteRunJudgment", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("dataflow: chart feeds pdf for real", check_dataflow_chart_feeds_pdf),
    ("arete virtue-judges the real run", check_arete_judges_the_real_run),
    ("the persian report narrates the judgment", check_report_narrates_judgment),
    ("the history carries excellence durably", check_history_carries_excellence),
    ("analytics reports the mean excellence", check_analytics_report_mean_excellence),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="ARETĒ run-judgment probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: ARETĒ JUDGES THE PLATFORM'S OWN WORK (داوری بر کار واقعی)")
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

    print("\nALL CHECKS PASSED — THE MIND JUDGES ITS OWN REAL WORK" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())