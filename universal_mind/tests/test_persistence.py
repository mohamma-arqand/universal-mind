"""Tests for the persistent runtime — durable local ledger + restart recovery."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from universal_mind.io.gateway import Gateway, ScriptedProvider
from universal_mind.memory.store import LocalJSONLStore
from universal_mind.runtime import (
    open_persistent_harness,
    persistent_store,
    recover_ledger,
)


def test_local_store_persists_to_disk() -> None:
    """Records appended to a LocalJSONLStore survive a fresh instance on the same dir."""
    with TemporaryDirectory() as d:
        store = LocalJSONLStore(directory=d, filename="ledger.jsonl")
        store.append({"owner_id": "s", "kind": "a", "payload": {"n": 1}})
        store.append({"owner_id": "s", "kind": "a", "payload": {"n": 2}})
        assert Path(d, "ledger.jsonl").is_file()
        reopened = LocalJSONLStore(directory=d, filename="ledger.jsonl")
        assert len(list(reopened.read_all())) == 2


def test_recover_ledger_empty_directory() -> None:
    """recover_ledger is safe on an empty dir and returns []."""
    with TemporaryDirectory() as d:
        assert recover_ledger(d) == []


def test_open_persistent_harness_writes_ledger() -> None:
    """A composed run over a persistent store writes a recoverable audit trail."""
    with TemporaryDirectory() as d:
        harness = open_persistent_harness(Gateway([ScriptedProvider(["persistent answer"])]), d)
        report = harness.run("persist", "write me to disk")
        assert report.ok is True
        records = recover_ledger(d)
        kinds = {r.get("kind") for r in records}
        assert "capability_registration" in kinds
        assert "intent_received" in kinds
        assert "capability_result" in kinds


def test_restart_recovers_history() -> None:
    """A brand-new harness over the same directory sees the earlier history."""
    with TemporaryDirectory() as d:
        first = open_persistent_harness(Gateway([ScriptedProvider(["answer one"])]), d)
        assert first.run("persist", "intent A").ok is True
        n_after_first = len(recover_ledger(d))

        # Simulate a restart: fresh harness, same directory, different provider.
        second = open_persistent_harness(Gateway([ScriptedProvider(["answer two"])]), d)
        assert second.run("persist", "intent B").ok is True
        n_after_second = len(recover_ledger(d))

        assert n_after_second > n_after_first
        assert n_after_first > 0


def test_prometheus_reads_persisted_ledger() -> None:
    """Prometheus can evolve over the persisted ledger after a restart."""
    from universal_mind.prometheus import InMemoryPrometheus

    with TemporaryDirectory() as d:
        harness = open_persistent_harness(Gateway([ScriptedProvider(["ok"])]), d)
        harness.run("persist", "seed history")
        report = InMemoryPrometheus(store=persistent_store(d)).evolve()
        assert report.metrics.executions == 1


def test_recover_ledger_returns_dict_records() -> None:
    """Recovered records are dicts carrying 'kind' and 'payload'."""
    with TemporaryDirectory() as d:
        harness = open_persistent_harness(Gateway([ScriptedProvider(["x"])]), d)
        harness.run("persist", "hey")
        rec = recover_ledger(d)[0]
        assert isinstance(rec, dict)
        assert "kind" in rec and "payload" in rec