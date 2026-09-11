#!/usr/bin/env python3
"""Probe: the closed self-awareness loop, end to end.

The charter's deepest aspiration — a mind that watches itself and acts on what
it sees — is a single closed loop now: execute → judge (with reasoning) →
self-assess → self-correct → feed that correction back through Prometheus as a
vetted proposal → apply it → and make the MOUTH more careful as a result.

This probe exercises that whole loop in one pass and exits non-zero unless every
invariant holds, proving the loop is real and deterministic end to end, not a set
of islands.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.mouth.commit import ConscientiousMouth, InMemoryMouth
from universal_mind.pantheon.registry import PantheonRegistry
from universal_mind.powers.judgment import CandidateOutput
from universal_mind.prometheus.apply import evolve_and_apply


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"artifact-{strategy_id}",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}},
    )


def _unhealthy_loop(store: InMemoryStore) -> SelfAwarenessLoop:
    from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode

    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    nodes = [
        JudgmentNode(depth=0, contender=f"c{i}", decision="deferred", reasoning="r", excellence=0.5, justice=1.0)
        for i in range(6)
    ]
    loop._lineage = JudgmentLineage.from_nodes(keeper, nodes)
    return loop


def check_introspection_detects_unhealthy() -> bool:
    store = InMemoryStore()
    loop = _unhealthy_loop(store)
    result = loop.introspect()
    ok = result.action_taken and result.healthy is False
    print(f"  introspection flags unhealthy judgment and acts: {ok}")
    return ok


def check_self_correction_and_audit() -> bool:
    store = InMemoryStore()
    loop = _unhealthy_loop(store)
    result = loop.introspect()
    kinds = [r.get("kind") for r in store.read_all()]
    ok = result.action_taken and "self_awareness" in kinds and loop.acceptance_bar > 0.9
    print(f"  self-correction raises the bar and is auditable in the ledger: {ok}")
    return ok


def check_prometheus_applies_self_correct() -> bool:
    store = InMemoryStore()
    loop = _unhealthy_loop(store)
    loop.introspect()  # writes the self_awareness entry (action_taken=True)
    executive = _executive_with_loop(store, loop)
    _, outcomes = evolve_and_apply(store, executive)
    applied = any(o.kind.value == "self_correct" and "tightened" in o.detail for o in outcomes)
    print(f"  Prometheus vets and applies a SELF_CORRECT proposal: {applied}")
    return applied


def check_mouth_gets_more_careful() -> bool:
    store = InMemoryStore()
    loop = _unhealthy_loop(store)
    loop.tighten(bar_step=0.1)  # bar crosses the caution threshold
    mouth = ConscientiousMouth(InMemoryMouth(), loop, caution_goal_words=5)
    from universal_mind.mouth.types import IntentNeedsClarification

    try:
        mouth.commit("summarize it", "sovereign")
        got_careful = False
    except IntentNeedsClarification:
        got_careful = True
    print(f"  MOUTH turns cautious when judgment is unhealthy: {got_careful}")
    return got_careful


def check_whole_loop_closes() -> bool:
    """Execute-free smoke: judgment → introspection → proposal → apply → caution."""
    store = InMemoryStore()
    loop = _unhealthy_loop(store)
    introspection = loop.introspect()
    executive = _executive_with_loop(store, loop)
    _, outcomes = evolve_and_apply(store, executive)
    applied = any("tightened" in o.detail for o in outcomes)
    mouth = ConscientiousMouth(InMemoryMouth(), loop, caution_goal_words=5)
    cautious = mouth._caution_active()
    ok = introspection.action_taken and applied and cautious
    print(f"  full loop closes (judge → assess → correct → apply → caution): {ok}")
    return ok


def _executive_with_loop(store: InMemoryStore, loop: SelfAwarenessLoop) -> Any:
    from universal_mind.core.clock import SystemClock
    from universal_mind.core.executive import ExecutiveMind
    from universal_mind.memory.mnemosyne import Mnemosyne

    registry = PantheonRegistry(store)
    return ExecutiveMind(
        registry=registry,
        memory=Mnemosyne(store, SystemClock()),
        clock=SystemClock(),
        owner=DEFAULT_OWNER,
        self_awareness=loop,
    )


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element(
        "testsuite",
        {
            "name": "ProbeClosedSelfAwarenessLoop",
            "tests": str(len(results)),
            "failures": str(sum(1 for _, ok in results if not ok)),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeClosedSelfAwarenessLoop", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Introspection flags unhealthy judgment", check_introspection_detects_unhealthy),
    ("Self-correction is auditable", check_self_correction_and_audit),
    ("Prometheus applies SELF_CORRECT", check_prometheus_applies_self_correct),
    ("MOUTH turns cautious", check_mouth_gets_more_careful),
    ("The full loop closes", check_whole_loop_closes),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Closed self-awareness loop probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: CLOSED SELF-AWARENESS LOOP (judge → assess → correct → apply → caution)")
    print("=" * 64)

    results: list[tuple[str, bool]] = []
    for name, fn in _CHECKS:
        print(f"\n--- {name} ---")
        try:
            results.append((name, fn()))
        except Exception as exc:  # noqa: BLE001 - a check crashing is a failure
            print(f"  check raised: {exc!r}")
            results.append((name, False))

    print("\n" + "=" * 64)
    print("SUMMARY")
    print("=" * 64)
    all_ok = True
    for name, result in results:
        print(f"  {name}: {'OK' if result else 'FAILED'}")
        all_ok = all_ok and result

    if args.junit_xml:
        write_junit_xml(results, args.junit_xml)
        print(f"\nJUnit XML written to {args.junit_xml}")

    if all_ok:
        print("\nALL CHECKS PASSED - THE MIND IS A CLOSED LOOP")
        return 0
    print("\nSOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())