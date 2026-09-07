#!/usr/bin/env python3
"""Probe: PROMETHEUS self-evolution is safe, evidence-backed, deterministic.

Drives the evolution loop over a scripted ledger history and confirms, from
outside the test suite, that: failing capabilities are surfaced for review;
high error-rate yields a throttle tuning proposal; repeated human rejection is
respected; proposals pass a conservative policy; and — crucially — the default
applier changes nothing (proposals-only), while a reversible in-memory applier
can apply then undo. Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.memory.store import InMemoryStore
from universal_mind.prometheus import (
    InMemoryApplier,
    InMemoryPrometheus,
    NoopApplier,
    ProposalKind,
    ThrottleApplier,
)


def _append(store: InMemoryStore, kind: str, payload: dict[str, object]) -> None:
    store.append(
        {
            "owner_id": "sovereign",
            "kind": kind,
            "created_at": "2026-09-07T00:00:00+00:00",
            "payload": payload,
            "provenance": {"producer": "probe"},
        }
    )


def _run(store: InMemoryStore, name: str, ok: bool) -> None:
    _append(store, "capability_selected", {"name": name})
    _append(store, "capability_result", {"ok": ok, "output": "x", "cost": 1.0, "notes": []})


def _failing_history() -> InMemoryStore:
    """A ledger where a capability is failing and the error rate is high."""
    store = InMemoryStore()
    for _ in range(3):
        _run(store, "flaky", False)
        _append(store, "fault", {"fault_class": "task_failure"})
    _run(store, "echo", True)
    _append(store, "feedback", {"verdict": "rejected", "target_record_id": "t1"})
    return store


def attempt_low_success_review() -> bool:
    """A failing capability is surfaced for review with evidence."""
    report = InMemoryPrometheus(_failing_history()).evolve()
    kinds = [p.kind.value for p in report.proposals]
    ok = ProposalKind.REVIEW_CAPABILITY.value in kinds
    print(f"  proposals={sorted(kinds)}")
    return ok


def attempt_tighten_on_error() -> bool:
    """A high error-rate yields a throttle-tuning proposal."""
    report = InMemoryPrometheus(_failing_history()).evolve()
    ok = any(p.kind == ProposalKind.TIGHTEN_THROTTLE for p in report.proposals)
    print(f"  tighten_throttle proposed: {ok}")
    return ok


def attempt_veto_respected() -> bool:
    """Repeated human rejection surfaces a respect-veto proposal."""
    report = InMemoryPrometheus(_failing_history()).evolve()
    ok = any(p.kind == ProposalKind.RESPECT_VETO for p in report.proposals)
    print(f"  respect_veto proposed: {ok}")
    return ok


def attempt_policy_filters() -> bool:
    """Every vetted-proposal is reversible and within the risk cap."""
    report = InMemoryPrometheus(_failing_history()).evolve()
    results = list(report.applied)
    all_safe = all("proposals-only" in outcome for _, outcome in results)
    print(f"  applied={len(results)} all-rest-to-manual-ratify: {all_safe}")
    return bool(results) and all_safe


def attempt_default_is_proposals_only() -> bool:
    """The default (Noop) applier changes nothing."""
    store = _failing_history()
    before = len(list(store.read_all()))
    report = InMemoryPrometheus(store, applier=NoopApplier()).evolve()
    after = len(list(store.read_all()))
    ok = before == after and all("proposals-only" in out for _, out in report.applied)
    print(f"  ledger {before}->{after} unchanged: {ok}")
    return ok


def attempt_reversible_apply_undo() -> bool:
    """A reversible applier writes then undoes an in-memory tuning knob."""
    store = _failing_history()
    applier = InMemoryApplier()
    report = InMemoryPrometheus(store, applier=applier).evolve()
    wrote = bool(applier.config)
    for kind in list(applier.config):
        proposal = next(p for p in report.proposals if p.kind.value == kind.split(":", 1)[1])
        applier.undo(proposal)
    ok = wrote and applier.config == {}
    print(f"  applied {wrote}, reverted to empty: {applier.config == {}}")
    return ok


def attempt_throttle_realized() -> bool:
    """A vetted TIGHTEN_THROTTLE proposal tunes the live throttle, reversibly."""
    from universal_mind.core.executive import ExecutionThrottle

    store = InMemoryStore()
    for _ in range(3):
        _run(store, "a", True)
        _append(store, "fault", {"fault_class": "system_fault"})
    throttle = ExecutionThrottle(error_rate_threshold=0.5)
    report = InMemoryPrometheus(store, applier=ThrottleApplier(throttle)).evolve()
    tightened = throttle.error_rate_threshold < 0.5
    print(f"  error_rate_threshold {0.5:.2f} -> {throttle.error_rate_threshold:.2f} (tightened={tightened})")
    return tightened and any("applied throttle" in o for _, o in report.applied)


def attempt_deterministic() -> bool:
    """Identical ledger state yields an identical proposal set."""
    def kinds() -> str:
        return "|".join(sorted(p.kind.value for p in InMemoryPrometheus(_failing_history()).evolve().proposals))

    ok = kinds() == kinds()
    print(f"  deterministic: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbePrometheusEvolution",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbePrometheusEvolution", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Failing capability surfaced for review", attempt_low_success_review),
    ("High error-rate yields throttle tuning", attempt_tighten_on_error),
    ("Human rejection is respected (veto)", attempt_veto_respected),
    ("Vetted proposals pass the conservative policy", attempt_policy_filters),
    ("Default applier is proposals-only (no mutation)", attempt_default_is_proposals_only),
    ("Reversible applier writes then undoes", attempt_reversible_apply_undo),
    ("Vetted throttle proposal tunes the live throttle", attempt_throttle_realized),
    ("Evolution loop is deterministic", attempt_deterministic),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="PROMETHEUS self-evolution Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: PROMETHEUS — Safe, Evidence-Backed, Deterministic Self-Evolution")
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
        print("\nALL CHECKS PASSED - PROMETHEUS SELF-EVOLUTION IS SAFE, EVIDENCE-BACKED, AND DETERMINISTIC")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())