#!/usr/bin/env python3
"""Probe: self-evolution is *applied* to the live executive, reversibly.

Runs a Prometheus pass and realizes the vetted proposals on a real
ExecutiveMind: a high error-rate tightens the throttle and a failing
capability installs a fallback chain — both reversible and deterministic.
Exit 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.core.clock import SystemClock
from universal_mind.core.executive import ExecutionThrottle, ExecutiveMind
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.pantheon.registry import PantheonRegistry
from universal_mind.prometheus import (
    FallbackOrderApplier,
    ProposalKind,
    ThrottleApplier,
    evolve_and_apply,
)
from universal_mind.prometheus.proposer import EvolutionProposal, Risk


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


def _executive(throttle_threshold: float = 0.5) -> ExecutiveMind:
    store = InMemoryStore()
    return ExecutiveMind(
        registry=PantheonRegistry(store),
        memory=Mnemosyne(store, SystemClock()),
        clock=SystemClock(),
        throttle=ExecutionThrottle(error_rate_threshold=throttle_threshold),
    )


def _store() -> InMemoryStore:
    """3 ok runs + 3 faults (high error rate) + 3 failed runs on 'flaky'."""
    store = InMemoryStore()
    for _ in range(3):
        _append(store, "capability_result", {"ok": True, "output": "x", "cost": 1.0, "notes": []})
        _append(store, "fault", {"fault_class": "task_failure"})
    for _ in range(3):
        _append(store, "capability_selected", {"name": "flaky"})
        _append(store, "capability_result", {"ok": False, "output": "x", "cost": 1.0, "notes": []})
    return store


def attempt_throttle_tightened() -> bool:
    """A high error-rate proposal tightens the live throttle."""
    exe = _executive(throttle_threshold=0.5)
    _, outcomes = evolve_and_apply(_store(), exe)
    tightened = exe.throttle.error_rate_threshold < 0.5
    kinds = sorted({o.kind.value for o in outcomes})
    print(f"  throttle {exe.throttle.error_rate_threshold:.3f} (<0.5: {tightened})  kinds={kinds}")
    return tightened and ProposalKind.TIGHTEN_THROTTLE.value in kinds


def attempt_fallback_installed() -> bool:
    """A failing capability installs a real fallback chain on the executive."""
    exe = _executive()
    _, outcomes = evolve_and_apply(_store(), exe)
    chain = exe.error_handler.fallback_capability
    ok = chain == ["echo"] and ProposalKind.REORDER_FALLBACK.value in {o.kind.value for o in outcomes}
    print(f"  fallback_capability={chain!r}")
    return ok


def _proposal_like(kind: ProposalKind) -> EvolutionProposal:
    return EvolutionProposal(
        kind=kind, target="t", reason="r", risk=Risk.LOW,
        reversible=True, suggested_change="s", evidence={},
    )


def attempt_reversible_undo() -> bool:
    """The throttle and fallback mutations restore on undo."""
    exe = _executive(throttle_threshold=0.5)
    prev = exe.throttle.error_rate_threshold
    throttle = ThrottleApplier(exe.throttle)
    fallback = FallbackOrderApplier(exe.error_handler)
    _, outcomes = evolve_and_apply(_store(), exe, throttle=throttle, fallback=fallback)
    kind_set = {o.kind for o in outcomes}
    for kind in kind_set:
        if kind == ProposalKind.TIGHTEN_THROTTLE:
            throttle.undo(_proposal_like(kind))
        if kind == ProposalKind.REORDER_FALLBACK:
            fallback.undo(_proposal_like(kind))
    restored = (abs(exe.throttle.error_rate_threshold - prev) < 1e-9
                and exe.error_handler.fallback_capability is None)
    print(f"  restored throttle {exe.throttle.error_rate_threshold:.3f} fallback={exe.error_handler.fallback_capability!r}")
    return restored


def attempt_deterministic() -> bool:
    """Identical inputs produce an identical tightened threshold."""
    def run() -> float:
        exe = _executive(throttle_threshold=0.5)
        _, _outs = evolve_and_apply(_store(), exe)
        return exe.throttle.error_rate_threshold

    ok = run() == run()
    print(f"  deterministic threshold: {ok}")
    return ok


def attempt_all_proposals_handled() -> bool:
    """Every proposal yields an outcome via apply_proposal routing."""
    exe = _executive()
    _, outcomes = evolve_and_apply(_store(), exe)
    ok = len(outcomes) > 0 and all(o.detail for o in outcomes)
    print(f"  outcomes={len(outcomes)} all with detail: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    """Write probe results to JUnit XML."""
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeEvolutionApply",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, r in results if not r)),
            "errors": "0",
            "time": "0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeEvolutionApply", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("High error-rate tightens the live throttle", attempt_throttle_tightened),
    ("Failing capability installs a fallback chain", attempt_fallback_installed),
    ("Mutations are reversible (undo restores)", attempt_reversible_undo),
    ("Evolution application is deterministic", attempt_deterministic),
    ("Every proposal has a handled outcome", attempt_all_proposals_handled),
]


def main() -> int:
    """Run every probe check and exit non-zero if any fails."""
    parser = argparse.ArgumentParser(description="Self-Evolution Apply Probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 60)
    print("PROBE: PROMETHEUS SELF-EVOLUTION IS APPLIED TO THE RUNNING EXECUTIVE")
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
        print("\nALL CHECKS PASSED - SELF-EVOLUTION IS CONSEQUENTIAL, REVERSIBLE, AND DETERMINISTIC")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())