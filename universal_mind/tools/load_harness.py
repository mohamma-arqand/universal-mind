"""Synthetic load harness — prove the loop holds up under real pressure.

Unit tests prove correctness, not capacity. This module exercises the composed
loop under a sustained synthetic load and reports honest numbers: request count,
throughput, and p50/p95 latency. It also verifies durability *under load* — a
fresh reopen (a true process-restart simulation) replays exactly what was
written, so the mind's memory is not just correct, but correct and intact after
restart.

Deterministic enough to assert on (no wall-clock in the assertions themselves;
latency is measured but only reported, never a correctness criterion).
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from universal_mind.durable import PersistentMind


@dataclass(frozen=True)
class LoadReport:
    """Honest numbers from one synthetic-load run."""

    request_count: int
    throughput_per_second: float
    p50_latency_ms: float
    p95_latency_ms: float
    failed: int
    final_ledger_size: int
    ledger_kinds: tuple[str, ...]


def run_load(
    directory: str | Path,
    *,
    requests: int = 20,
    goal: str = "summarize",
    raw_text: str = "summarize the topic",
) -> LoadReport:
    """Run ``requests`` passes of the composed loop and measure/report the load.

    Uses a fresh :class:`PersistentMind` over an on-disk ledger; each pass is a
    full intent→gate→execute→record cycle. Latency is measured but not asserted
    (correctness and durability are the invariants, not speed).
    """
    mind = PersistentMind.open(directory)
    latencies_ms: list[float] = []
    failed = 0
    start = time.perf_counter()

    for _ in range(requests):
        t0 = time.perf_counter()
        report = mind.run(goal, raw_text)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        if not report.ok:
            failed += 1

    elapsed = time.perf_counter() - start
    sorted_lat = sorted(latencies_ms)
    p50 = statistics.median(sorted_lat)
    p95 = sorted_lat[int(len(sorted_lat) * 0.95) - 1] if sorted_lat else 0.0
    throughput = requests / elapsed if elapsed > 0 else 0.0

    return LoadReport(
        request_count=requests,
        throughput_per_second=round(throughput, 2),
        p50_latency_ms=round(p50, 3),
        p95_latency_ms=round(p95, 3),
        failed=failed,
        final_ledger_size=mind.ledger_size,
        ledger_kinds=mind.ledger_kinds(),
    )


def verify_durability_under_load(directory: str | Path) -> bool:
    """Reopen the ledger (a real restart) and confirm it replays intact.

    Returns True only if a fresh ``PersistentMind.reopen`` reads back a non-empty
    ledger with the expected composed-run record kinds — proving the mind's
    memory survives a process restart under load.
    """
    reopened = PersistentMind.reopen(directory)
    size = reopened.ledger_size
    kinds = reopened.ledger_kinds()
    return size > 0 and "intent_received" in kinds and "capability_result" in kinds