"""The drift detector — the platform notices its own slow rot.

R44 item 14: a threshold like "hot path < 150ms" only catches catastrophe.
The real killer is DRIFT: each change adds 5ms and nothing ever fires until
the run costs 3× its birth cost. Two drifts are measured:

1. PERFORMANCE — a hot-path benchmark against a committed ``perf_baseline.json``.
   The gate is RELATIVE (ratio vs baseline), so a slow CI machine or a fast
   laptop cannot lie: ratio > SLOWDOWN_FACTOR = red, and the baseline itself
   is never silently rewritten — it updates only through an explicit refresh
   with the old/new numbers printed.
2. REPORT LAWS — a golden corpus of (command → report) pairs. The reporter's
   Persian sentences are laws (what must be present, what must never leak);
   a change that drops a promise or lets an English key leak is drift even
   though every unit test still passes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASELINE_PATH = Path(__file__).resolve().parent / "perf_baseline.json"
SLOWDOWN_FACTOR = 2.0  # ratio vs baseline that means "too slow"
HOT_COMMAND = "میانگین ۵ و ۷ را حساب کن"
HOT_WARMUP = 1
HOT_RUNS = 10


@dataclass(frozen=True)
class DriftVerdict:
    """One gate's verdict, with the numbers that produced it."""

    gate: str
    ok: bool
    detail: str


def measure_hot_path() -> float:
    """Median ms per simple run on the LIVE router (no mocks)."""
    import statistics

    from universal_mind.persian_router import route_and_run

    for _ in range(HOT_WARMUP):
        route_and_run(HOT_COMMAND)
    samples: list[float] = []
    for _ in range(HOT_RUNS):
        t0 = time.perf_counter()
        route_and_run(HOT_COMMAND)
        samples.append((time.perf_counter() - t0) * 1000)
    return float(statistics.median(samples))


def load_baseline() -> dict[str, Any] | None:
    """The committed baseline, or None (an honest 'never measured')."""
    if not BASELINE_PATH.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        return data
    except (OSError, ValueError):
        return None


def write_baseline(ms: float) -> dict[str, Any]:
    """EXPLICIT refresh — never called by a gate, only by a deliberate act."""
    payload = {
        "hot_path_ms": round(ms, 1),
        "command": HOT_COMMAND,
        "runs": HOT_RUNS,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    BASELINE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def check_perf_drift() -> DriftVerdict:
    """Ratio vs baseline. No baseline = an honest 'unmeasured', never a pass."""
    baseline = load_baseline()
    ms = measure_hot_path()
    if baseline is None or not baseline.get("hot_path_ms"):
        return DriftVerdict(
            "perf",
            False,
            f"hot path = {ms:.0f}ms اما خط مبنا نیست — `write_baseline` را صادقانه اجرا کن",
        )
    base_ms = float(baseline["hot_path_ms"])
    ratio = ms / base_ms if base_ms > 0 else 0.0
    ok = ratio < SLOWDOWN_FACTOR
    detail = f"hot path {ms:.0f}ms / مبنا {base_ms:.0f}ms = {ratio:.2f}× (سقف {SLOWDOWN_FACTOR}×)"
    return DriftVerdict("perf", ok, detail)


# The REPORT-LAW golden corpus: each entry is (command, law). A law is a dict
# with `must_contain` (promises kept) and `must_not_contain` (leaks banned).
# These pin the REPORTER's behavior on commands whose full runs are cheap and
# deterministic — drift here means a Persian promise silently disappeared.
GOLDEN_REPORT_CORPUS: list[tuple[str, dict[str, list[str]]]] = [
    ("میانگین ۵ و ۷ را حساب کن",
     {"must_contain": ["میانگین"], "must_not_contain": []}),
    ("امروز چی کار کردی؟",
     {"must_contain": [], "must_not_contain": ["نشناختم"]}),
    ("چی بلدی؟",
     {"must_contain": ["قابلیت"], "must_not_contain": ["نشناختم"]}),
    ("خدانگهدار",
     {"must_contain": ["منتظر"], "must_not_contain": []}),
]


def check_report_drift() -> list[DriftVerdict]:
    """Every golden pair through the LIVE router; each violation is drift."""
    from universal_mind.persian_router import route_and_run

    verdicts: list[DriftVerdict] = []
    for command, law in GOLDEN_REPORT_CORPUS:
        try:
            payload: Any = route_and_run(command)
            report = str(payload.get("agent_report", ""))
        except Exception as exc:  # noqa: BLE001 — a crash IS the drift
            verdicts.append(DriftVerdict("report", False, f"{command[:20]}: crashed: {exc}"))
            continue
        missing = [p for p in law["must_contain"] if p not in report]
        leaked = [b for b in law["must_not_contain"] if b in report]
        ok = not missing and not leaked
        detail = f"{command[:24]}: "
        if missing:
            detail += f"وعدههای جاافتاده: {missing}"
        if leaked:
            detail += f"نشتهای تازه: {leaked}"
        verdicts.append(DriftVerdict("report", ok, detail if not ok else "قوانین پابرجا"))
    return verdicts


