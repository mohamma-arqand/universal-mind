"""Tests for observable deploy metrics — real numbers from the ledger."""

from __future__ import annotations

from universal_mind.memory.store import InMemoryStore
from universal_mind.observability.metrics import (
    deploy_metrics_from_store,
    derive_deploy_metrics,
)


def _record(kind: str, ok: bool | None = None, created: str = "2026-09-11T10:00:00") -> dict[str, object]:
    rec: dict[str, object] = {"kind": kind, "created_at": created}
    if ok is not None:
        rec["payload"] = {"ok": ok}
    return rec


def test_derive_counts_executions_successes_faults() -> None:
    records = [
        _record("capability_result", ok=True),
        _record("capability_result", ok=True),
        _record("capability_result", ok=False),
        _record("fault"),
    ]
    metrics = derive_deploy_metrics(records)
    assert metrics.executions == 3
    assert metrics.successes == 2
    assert metrics.faults == 1
    assert metrics.error_rate == 0.25


def test_error_rate_is_zero_without_activity() -> None:
    metrics = derive_deploy_metrics([])
    assert metrics.error_rate == 0.0
    assert metrics.executions == 0


def test_kinds_are_counted() -> None:
    records = [_record("capability_result", True), _record("fault"), _record("fault")]
    metrics = derive_deploy_metrics(records)
    assert metrics.kinds["capability_result"] == 1
    assert metrics.kinds["fault"] == 2


def test_last_activity_is_latest_timestamp() -> None:
    records = [_record("x", created="2026-09-11T10:00:00"), _record("y", created="2026-09-11T12:00:00")]
    metrics = derive_deploy_metrics(records)
    assert metrics.last_activity == "2026-09-11T12:00:00"


def test_from_store_reads_real_records() -> None:
    store = InMemoryStore()
    store.append(_record("capability_result", ok=True))
    metrics = deploy_metrics_from_store(store)
    assert metrics.executions == 1
    assert metrics.successes == 1


def test_metrics_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    m = derive_deploy_metrics([])
    try:
        m.executions = 99  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True