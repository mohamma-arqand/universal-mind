"""Shared knowledge — what one tool learned, another can use (Phase 5a).

Phase D fused outputs; Phase E ranked tools. Phase 5a closes the *memory* gap:
when a tool produces a durable fact (an address, a token, a setting), that fact
should be available to every other tool in the pipeline — not siloed inside the
one tool that happened to discover it.

This module provides a small, namespaced knowledge store: tools publish named
facts with provenance (who learned it, when), and any tool can read them by name.
It is deliberately small and explicit — no free-text retrieval, just named slots —
so the sharing is auditable and deterministic, not a hidden side channel.

This is the substrate for "the past shapes the next run" across tools, the same
remembering promise Mnemosyne already keeps for the mind as a whole.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KnowledgeFact:
    """One shared fact with provenance."""

    name: str
    value: Any
    produced_by: str          # the tool name that published it


class SharedKnowledge:
    """A namespaced, provenance-carrying store of cross-tool facts.

    ``publish`` records (or overwrites) a named fact; ``read`` returns it (or a
    default); ``latest`` returns facts with their producer, for auditability.
    Deterministic and local — a plain in-memory dictionary keyed by name.
    """

    def __init__(self) -> None:
        self._facts: dict[str, KnowledgeFact] = {}

    def publish(self, name: str, value: Any, produced_by: str) -> None:
        """Record (or overwrite) a named fact with its producer."""
        self._facts[name] = KnowledgeFact(name=name, value=value, produced_by=produced_by)

    def read(self, name: str, default: Any = None) -> Any:
        """Return a fact's value, or ``default`` if never published."""
        fact = self._facts.get(name)
        return fact.value if fact is not None else default

    def known(self, name: str) -> bool:
        """True if the fact has been published."""
        return name in self._facts

    def latest(self) -> tuple[KnowledgeFact, ...]:
        """All shared facts with their producer (auditable)."""
        return tuple(self._facts.values())


__all__ = ["KnowledgeFact", "SharedKnowledge"]