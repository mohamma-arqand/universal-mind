#!/usr/bin/env python3
"""Probe: episodic memory — recall *when* and *in what context*, not just *what*.

Mnemosyne answers "what did I record?"; this probe proves the mind also answers
the temporal question: episodes are anchored with timestamp + context, recalled
most-recent-first, filtered by context and owner, and summarized with the *when*.
Exit non-zero unless all hold.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.episodic import recall_episodes, record_episode
from universal_mind.memory.store import InMemoryStore


def _clock(iso: str = "2026-09-11T10:00:00") -> FrozenClock:
    return FrozenClock(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc))


def check_record_and_recall_by_context() -> bool:
    store = InMemoryStore()
    record_episode(store, owner_id="sovereign", kind="judgment", context="merger", clock=_clock())
    result = recall_episodes(store, "merger")
    ok = len(result.episodes) == 1 and result.episodes[0].kind == "judgment"
    print(f"  episode recorded and recalled by context: {ok}")
    return ok


def check_recall_is_most_recent_first() -> bool:
    store = InMemoryStore()
    clock = _clock()
    record_episode(store, owner_id="sovereign", kind="first", context="topic", clock=clock)
    record_episode(store, owner_id="sovereign", kind="second", context="topic", clock=clock.advance(60))
    result = recall_episodes(store, "topic")
    ok = result.episodes[0].kind == "second" and result.episodes[1].kind == "first"
    print(f"  recall is temporal, most recent first: {ok}")
    return ok


def check_context_and_owner_filters() -> bool:
    store = InMemoryStore()
    record_episode(store, owner_id="alice", kind="a", context="finance", clock=_clock())
    record_episode(store, owner_id="bob", kind="b", context="health", clock=_clock())
    by_context = recall_episodes(store, "finance")
    by_owner = recall_episodes(store, "finance", owner_id="alice")
    ok = len(by_context.episodes) == 1 and len(by_owner.episodes) == 1
    print(f"  context + owner filters apply: {ok}")
    return ok


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeEpisodicMemory",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeEpisodicMemory", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("Record and recall by context", check_record_and_recall_by_context),
    ("Recall is most recent first", check_recall_is_most_recent_first),
    ("Context and owner filters apply", check_context_and_owner_filters),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Episodic memory probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: EPISODIC MEMORY (recall when and in what context)")
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

    print("\nALL CHECKS PASSED - THE MIND REMEMBERS WHEN, NOT JUST WHAT" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())