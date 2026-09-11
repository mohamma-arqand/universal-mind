"""Observable deploy metrics — real numbers from the ledger, not just "tests pass".

Unit tests prove correctness, but a *deployed* mind must be observable: how many
executions, how many faults, what is the error rate, how is memory growing. This
module derives deploy metrics from the append-only ledger — a plain,
serializable snapshot suitable for scraping by Prometheus / OTel — so the running
mind reports honest operational telemetry, not a green checkmark.

Deterministic and pure: it reads the store, never emits to a network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DeployMetrics:
    """Operational metrics derived from the ledger."""

    total_records: int
    executions: int
    successes: int
    faults: int
    error_rate: float
    kinds: dict[str, int] = field(default_factory=dict)
    last_activity: str = ""       # ISO timestamp of the most recent record, if any


def derive_deploy_metrics(records: list[dict[str, Any]]) -> DeployMetrics:
    """Derive operational metrics from a list of ledger records.

    ``executions`` counts ``capability_result`` records; ``successes`` is the
    subset with ``ok=True``; ``faults`` counts ``fault`` records; ``error_rate``
    is faults / (executions + faults) when any activity exists, else 0.0.
    """
    executions = 0
    successes = 0
    faults = 0
    kinds: dict[str, int] = {}
    last_activity = ""

    for record in records:
        kind = str(record.get("kind", "unknown"))
        kinds[kind] = kinds.get(kind, 0) + 1
        created = record.get("created_at")
        if isinstance(created, str) and created > last_activity:
            last_activity = created

        payload = record.get("payload")
        if kind == "capability_result":
            executions += 1
            if isinstance(payload, dict) and payload.get("ok") is True:
                successes += 1
        elif kind == "fault":
            faults += 1

    denominator = executions + faults
    error_rate = faults / denominator if denominator else 0.0

    return DeployMetrics(
        total_records=len(records),
        executions=executions,
        successes=successes,
        faults=faults,
        error_rate=round(error_rate, 4),
        kinds=kinds,
        last_activity=last_activity,
    )


def deploy_metrics_from_store(store: Any) -> DeployMetrics:
    """Derive deploy metrics from a MemoryStore (reads ``read_all()``)."""
    return derive_deploy_metrics(list(store.read_all()))