"""Distributed memory — several instances over one synchronized ledger.

A single-process mind forgets when the process dies and cannot see another mind's
experience. This module is the shared-ledger layer: multiple ``MemoryStore``
instances pointing at the same on-disk JSONL file are all *synchronized* — an
append by one instance is visible to every other on the next read, because each
read replays the file. This is a genuinely shared memory, not per-instance copies.

Deterministic and local: it uses ``LocalJSONLStore`` (append-only file, read-on-
every-access), so no network or lock is required for the reference contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal_mind.memory.store import LocalJSONLStore


@dataclass(frozen=True)
class SharedLedger:
    """Two (or more) store handles over one synchronized on-disk ledger."""

    directory: Path
    filename: str = "ledger.jsonl"


def open_shared_ledger(directory: str | Path, *, instances: int = 2, filename: str = "ledger.jsonl") -> list[LocalJSONLStore]:
    """Open ``instances`` store handles over the same on-disk ledger file.

    Each handle reads the file on every access, so they are synchronized: writing
    through one is immediately visible through the others (next read).
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return [LocalJSONLStore(directory=path, filename=filename) for _ in range(instances)]


def append_through(store: LocalJSONLStore, owner_id: str, kind: str, payload: dict[str, Any]) -> str:
    """Append one record through a store handle (mirrors Mnemosyne's shape)."""
    return store.append(
        {
            "owner_id": owner_id,
            "kind": kind,
            "payload": payload,
            "provenance": {"producer": "shared"},
        }
    )


def is_synchronized(stores: list[LocalJSONLStore]) -> bool:
    """True if every store sees the same record ids (a real shared memory)."""
    if not stores:
        return True
    baseline = {r.get("id") for r in stores[0].read_all()}
    return all({r.get("id") for r in s.read_all()} == baseline for s in stores[1:])