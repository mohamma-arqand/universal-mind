"""Durable, restartable face over a local on-disk ledger.

The default integration/runtime stores are in-memory (volatile). This module
wraps the composed integration harness with a :class:`LocalJSONLStore` so the
ledger lives on disk and survives a process restart — reopening the same
directory replays exactly what was written (the store reads from the file on
every access, so a brand-new instance is a true reload).

Usage::
    mind = PersistentMind.open("/var/lib/universal-mind")
    mind.run("summarize", "write me")
    # later, in a fresh process:
    mind2 = PersistentMind.reopen("/var/lib/universal-mind")
    assert mind2.ledger_size == mind.ledger_size
"""

from __future__ import annotations

from pathlib import Path

from universal_mind.integration import InMemoryIntegrationHarness, IntegrationReport
from universal_mind.io.gateway import EchoProvider, Gateway
from universal_mind.memory.store import LocalJSONLStore


class PersistentMind:
    """Composed runtime whose ledger is persisted to disk via LocalJSONLStore."""

    def __init__(self, directory: str | Path, filename: str = "ledger.jsonl") -> None:
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self.store = LocalJSONLStore(directory=self._directory, filename=filename)
        self._filename = filename
        self.harness = InMemoryIntegrationHarness(
            Gateway([EchoProvider(cost=1.0)]),
            store=self.store,
        )

    @classmethod
    def open(cls, directory: str | Path, filename: str = "ledger.jsonl") -> PersistentMind:
        """Open (creating a fresh runtime over) an on-disk ledger directory."""
        return cls(directory, filename=filename)

    @classmethod
    def reopen(cls, directory: str | Path, filename: str = "ledger.jsonl") -> PersistentMind:
        """Reopen an existing ledger directory as if after a process restart."""
        return cls(directory, filename=filename)

    def run(self, goal: str, raw_text: str) -> IntegrationReport:
        """Execute an intent through the composed system (persisted immediately)."""
        return self.harness.run(goal, raw_text)

    @property
    def ledger_size(self) -> int:
        """Number of live records currently on disk."""
        return sum(1 for _ in self.store.read_all())

    @property
    def directory(self) -> Path:
        """The on-disk ledger directory."""
        return self._directory

    def ledger_kinds(self) -> tuple[str, ...]:
        """Distinct record kinds present in the on-disk ledger (ordered)."""
        kinds = sorted({str(r.get("kind")) for r in self.store.read_all()})
        return tuple(kinds)