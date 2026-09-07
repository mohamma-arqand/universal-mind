"""Persistent runtime — compose the system over a durable local ledger.

Everything in the project also runs against the volatile :class:`InMemoryStore`.
This module makes the *durable* story explicit: point a composed harness at a
directory and its full audit trail is written incrementally to local JSON Lines,
survives a restart (a brand-new instance over the same directory sees the prior
history), and can later be recovered for audit or fed back to Prometheus.

No external provider, API, or model is involved — the only I/O is the local
ledger on disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from universal_mind.integration import InMemoryIntegrationHarness
from universal_mind.io.gateway import Gateway
from universal_mind.memory.store import LocalJSONLStore


def persistent_store(directory: str | Path, *, filename: str = "ledger.jsonl") -> LocalJSONLStore:
    """Open (creating if needed) a durable LocalJSONLStore under ``directory``."""
    return LocalJSONLStore(directory=directory, filename=filename)


def open_persistent_harness(
    gateway: Gateway,
    directory: str | Path,
    *,
    filename: str = "ledger.jsonl",
) -> InMemoryIntegrationHarness:
    """A composed, runnable harness backed by a persistent local ledger.

    Reopening the same ``directory`` with a fresh harness is equivalent to a
    process restart: the new harness observes the ledger written before it.
    """
    return InMemoryIntegrationHarness(gateway, store=persistent_store(directory, filename=filename))


def recover_ledger(
    directory: str | Path,
    *,
    filename: str = "ledger.jsonl",
) -> list[dict[str, Any]]:
    """Return every record in the persisted ledger, for audit or recovery.

    Safe to call on an empty/absent directory (returns ``[]`` after creating it).
    """
    return list(persistent_store(directory, filename=filename).read_all())