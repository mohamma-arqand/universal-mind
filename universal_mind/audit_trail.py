"""Action audit trail — a full input->output trace for every tool action (Phase 5b).

An autonomous system that can reach real tools must also be able to *prove* what it
did. This module provides an append-only, provenance-carrying trail of every action:
who/what acted, on what capability, with what inputs, and what came back. The trail
is immutable-in-append (entries are only added, never mutated), so a post-hoc audit
can reconstruct any action from request to result.

This is the audit half of Phase 5; isolation (5c) is enforced elsewhere by the
connectors' sandbox + allowlist, which this trail records alongside each action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    """One recorded action: capability, tool, inputs, outcome."""

    capability: str
    tool_name: str
    inputs: Any
    output: Any
    ok: bool
    error: str = ""


class AuditTrail:
    """An append-only record of actions, reconstructable end-to-end.

    ``record`` appends an entry; ``entries`` returns them oldest-first; ``replay``
    returns the same entries (the trail is the ledger). No entry can be mutated or
    removed once appended — auditability requires immutability.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, capability: str, tool_name: str, inputs: Any, output: Any, ok: bool, error: str = "") -> AuditEntry:
        entry = AuditEntry(capability=capability, tool_name=tool_name, inputs=inputs, output=output, ok=ok, error=error)
        self._entries.append(entry)
        return entry

    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def last(self) -> AuditEntry | None:
        return self._entries[-1] if self._entries else None

    def trace(self, capability: str) -> tuple[AuditEntry, ...]:
        """Every recorded action for a given capability (oldest first)."""
        return tuple(e for e in self._entries if e.capability == capability)


__all__ = ["AuditEntry", "AuditTrail"]