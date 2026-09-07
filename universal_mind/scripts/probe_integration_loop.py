#!/usr/bin/env python3
"""Probe: the integration face closes the loop of the whole system.

Drives the composed runtime (ExecutiveMind + GatewayCapability + ARETĒ +
Prometheus) over a deterministic provider and confirms, from outside the test
suite, that a single intent produces: a successful audited execution, a gateway
output that wins ARETĒ arbitration over a baseline, an intact shared ledger,
and a Prometheus evolution pass. Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.integration import (
    InMemoryIntegrationHarness,
    IntegrationReport,
    UniversalMindRuntime,
)
from universal_mind.io.gateway import Gateway, ScriptedProvider


def _report() -> IntegrationReport:
    provider = ScriptedProvider(["A fair, accurate, verified summary of the request."])
    return InMemoryIntegrationHarness(Gateway([provider])).run(
        "summarize", "Please summarize this document"
    )


def attempt_execution_ok() -> bool:
    """The composed ExecutiveMind executes the intent successfully."""
    report = _report()
    ok = bool(report and report.execution_status == "ok")
    print(f"  execution_status: {report.execution_status} ok={ok}")
    return ok and report.ok is True


def attempt_gateway_wins_arbitration() -> bool:
    """The gateway output beats the baseline under ARETĒ."""
    report = _report()
    scores = {s.candidate_strategy_id: round(s.excellence, 3) for s in report.arbitration.scorecards}
    win = report.arbitration.winner_strategy_id == "gateway"
    print(f"  winner={report.arbitration.winner_strategy_id} scores={scores}")
    return win and scores["gateway"] > scores["baseline"]


def attempt_ledger_is_audited() -> bool:
    """The shared ledger carries the full ExecutiveMind audit trail."""
    provider = ScriptedProvider(["ok"])
    harness = InMemoryIntegrationHarness(Gateway([provider]))
    harness.run("summarize", "audit me")
    kinds = {r.get("kind") for r in harness.store.read_all()}
    required = {"capability_registration", "intent_received", "risk_assessment",
                "capability_selected", "capability_result"}
    missing = required - kinds
    print(f"  ledger kinds present: {sorted(required - missing)}")
    return not missing


def attempt_prometheus_observes_ledger() -> bool:
    """Prometheus runs an evolution pass over the same ledger without error."""
    report = _report()
    ok = isinstance(report.evolution_summary, str) and bool(report.evolution_summary)
    print(f"  evolution_summary: {report.evolution_summary!r}")
    return ok and isinstance(report.proposals, tuple)


def attempt_deterministic() -> bool:
    """Identical provider + inputs yield an identical composed outcome."""
    def once() -> tuple[str, str | None]:
        provider = ScriptedProvider(["Deterministic summary"])
        r = InMemoryIntegrationHarness(Gateway([provider])).run("summarize", "same")
        return r.execution_status, r.arbitration.winner_strategy_id

    ok = once() == once()
    print(f"  deterministic: {ok}")
    return ok


def attempt_protocol() -> bool:
    """The harness conforms to the UniversalMindRuntime protocol."""
    harness = InMemoryIntegrationHarness(Gateway([ScriptedProvider(["x"])]))
    ok = isinstance(harness, UniversalMindRuntime)
    print(f"  conforms to UniversalMindRuntime protocol: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeIntegrationLoop",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeIntegrationLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Composed ExecutiveMind executes successfully", attempt_execution_ok),
    ("Gateway output wins ARETĒ arbitration over baseline", attempt_gateway_wins_arbitration),
    ("Shared ledger carries the audit trail", attempt_ledger_is_audited),
    ("Prometheus evolves over the same ledger", attempt_prometheus_observes_ledger),
    ("Composed run is deterministic", attempt_deterministic),
    ("Harness conforms to the runtime protocol", attempt_protocol),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="Integration Loop Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: Integration Face — ExecutiveMind + Gateway + ARETĒ + Prometheus")
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
        print("\nALL CHECKS PASSED - THE COMPOSED SYSTEM RUNS END-TO-END AND CLOSES THE LOOP")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())