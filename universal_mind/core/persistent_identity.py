"""Persistent identity — continuous identity that survives a restart.

A fresh :class:`Identity` per session means the mind forgets *who it is* between
runs. This module is the continuity layer: it persists an identity into the
ledger (as an ``identity`` record) and can reconstruct the same owner on reopen,
so "I am sovereign across sessions" is a real, auditable claim — not a rebuilt
default.

Deterministic and local: it writes/reads the store; the identity itself stays an
immutable :class:`Identity`.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.core.identity import Identity
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class IdentityHandle:
    """A persisted identity plus whether it was recovered (vs newly created)."""

    identity: Identity
    recovered: bool


def persist_identity(store: MemoryStore, identity: Identity) -> str:
    """Write an identity into the ledger as an ``identity`` record; return its id."""
    return store.append(
        {
            "kind": "identity",
            "owner_id": identity.owner_id,
            "payload": {"owner_id": identity.owner_id, "display_name": identity.display_name},
            "provenance": {"producer": "PersistentIdentity"},
        }
    )


def recover_identity(store: MemoryStore, *, default: Identity | None = None) -> IdentityHandle:
    """Recover the most recent persisted identity, or fall back to ``default``.

    Returns ``recovered=True`` when a stored identity was found (the mind is the
    same owner as before a restart); otherwise ``recovered=False`` with a fresh
    default (no prior identity to continue).
    """
    identities = store.find(kind="identity")
    if identities:
        latest = identities[-1]
        payload = latest.get("payload", {})
        owner_id = str(payload.get("owner_id", default.owner_id if default else ""))
        display_name = str(payload.get("display_name", default.display_name if default else ""))
        return IdentityHandle(identity=Identity(owner_id=owner_id, display_name=display_name), recovered=True)

    default = default if default is not None else Identity(owner_id="sovereign", display_name="Owner")
    return IdentityHandle(identity=default, recovered=False)