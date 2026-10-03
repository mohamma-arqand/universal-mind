#!/usr/bin/env python3
"""Probe: THE INTELLIGENCE LAYER — the platform that ranks before it runs.

Four intelligence upgrades, live in the release gate:
  1. INTENT LENS — orderings ranked by REAL evidence (chain history, flow
     history, vocabulary overlap, standing); an UNSEEN chain never outranks
     a proven one;
  2. SEED MEMORY — «بلند بخوان» alone speaks the LAST REAL success (the
     honest refusal only when history is empty);
  3. FARTHEST RIVAL — the quality gate's candidate set can gain a genuinely
     different lens-chosen route, never a duplicate real run;
  4. SPEECH MEMORY — advice carries the winning run's proven params.

Exit non-zero unless every check holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_lens_ranks_proven_over_unseen() -> bool:
    from universal_mind.intent_lens import rank_routes, scored_fa

    ranked = rank_routes(
        [("data", "chart", "pdf"), ("pdf", "chart", "data")],
        "نمودار خطی از ۲ و ۵ و ۹ بساز و گزارشش کن",
    )
    ok = ranked[0].route == ("data", "chart", "pdf") and ranked[0].score > ranked[1].score
    print(f"  winner: {ranked[0].route} ({ranked[0].score}) vs {ranked[1].route} ({ranked[1].score})")
    print(f"  why: {scored_fa(ranked[0])}")
    return bool(ok)


def check_seed_speaks_the_last_success() -> bool:
    from universal_mind.persian_params import extract_params

    params = extract_params("بلند بخوان", "speech")
    ok = params.get("seeded") is True and bool(params.get("text"))
    print(f"  seed: {str(params.get('text'))[:60]!r}")
    return bool(ok)


def check_explicit_tail_wins_over_seed() -> bool:
    from universal_mind.persian_params import extract_params

    params = extract_params("بلند بخوان که گزارش آماده است", "speech")
    ok = params.get("seeded") is None and params.get("text") == "گزارش آماده است"
    print(f"  explicit: {params.get('text')!r}")
    return bool(ok)


def check_gate_dedupes_real_runs() -> bool:
    from universal_mind.quality_gate import run_with_quality_gate

    seen: list[tuple[str, ...]] = []

    def runner(candidate: tuple[str, ...]) -> dict[str, object]:
        seen.append(candidate)
        return {
            "ok": True, "route": list(candidate),
            "result": {"data": {"bytes": 100, "mean": 4.0, "n": 2}},
            "judgment": {"excellence": 0.95},
        }

    gate = run_with_quality_gate("نمودار بساز و ذخیره کن", ("data", "chart"), runner, bar=0.5)
    ok = gate.shipped.excellence >= 0.5 and len(seen) == len(set(seen))
    print(f"  runs={len(seen)} unique={len(set(seen))} shipped={gate.shipped.route}")
    return bool(ok)


def check_advice_carries_seeds() -> bool:
    from universal_mind.run_history import ChainAdvisor, RunHistory

    advice, seeds = ChainAdvisor(RunHistory()).advise_with_seeds("نمودار از ۲ و ۵ و ۹ بساز")
    ok = advice is not None and advice.route and (seeds is None or all(
        isinstance(p, dict) and p for p in seeds.values()
    ))
    print(f"  advice: {advice.route if advice else None} | seeds: {seeds}")
    return bool(ok)


def write_junit_xml(results: list[tuple[str, bool]], output_file: str) -> None:
    testsuite = ET.Element("testsuite", {
        "name": "ProbeIntelligenceLayer",
        "tests": str(len(results)),
        "failures": str(sum(1 for _, ok in results if not ok)),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    for name, ok in results:
        testcase = ET.SubElement(testsuite, "testcase", {"name": name, "classname": "ProbeIntelligenceLayer", "time": "0"})
        if not ok:
            ET.SubElement(testcase, "failure", {"message": f"Check {name} failed", "type": "AssertionError"})
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


_CHECKS: list[tuple[str, Callable[[], bool]]] = [
    ("lens: proven chains outrank unseen reshuffles", check_lens_ranks_proven_over_unseen),
    ("seed: «بلند بخوان» speaks the last real success", check_seed_speaks_the_last_success),
    ("explicit: the spoken tail wins over the seed", check_explicit_tail_wins_over_seed),
    ("gate: real runs are never duplicated", check_gate_dedupes_real_runs),
    ("advice: seeds carry the winning run's params", check_advice_carries_seeds),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Intelligence-layer probe")
    parser.add_argument("--junit-xml", help="Output JUnit XML file")
    args = parser.parse_args()

    print("=" * 64)
    print("PROBE: THE INTELLIGENCE LAYER (لنز، بذر، رقیب، حافظهی گفتار)")
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

    print("\nALL CHECKS PASSED — THE PLATFORM RANKS BEFORE IT RUNS" if all_ok else "\nSOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())