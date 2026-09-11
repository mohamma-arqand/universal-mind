"""Tests for persistent identity — the same owner survives a restart."""

from __future__ import annotations

from universal_mind.core.identity import Identity
from universal_mind.core.persistent_identity import (
    IdentityHandle,
    persist_identity,
    recover_identity,
)
from universal_mind.memory.store import InMemoryStore


def test_persist_then_recover_returns_same_owner() -> None:
    store = InMemoryStore()
    identity = Identity(owner_id="alice", display_name="Alice")
    persist_identity(store, identity)

    # A "restart" = a fresh recovery call over the same store.
    handle = recover_identity(store)
    assert handle.recovered is True
    assert handle.identity.owner_id == "alice"
    assert handle.identity.display_name == "Alice"


def test_recover_without_prior_identity_uses_default() -> None:
    store = InMemoryStore()
    handle = recover_identity(store)
    assert handle.recovered is False
    assert handle.identity.owner_id == "sovereign"


def test_recover_prefers_latest_identity() -> None:
    store = InMemoryStore()
    persist_identity(store, Identity("old", "Old"))
    persist_identity(store, Identity("new", "New"))
    handle = recover_identity(store)
    assert handle.identity.owner_id == "new"


def test_identity_handle_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    h = IdentityHandle(Identity("x", "X"), True)
    try:
        h.recovered = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_persist_returns_a_record_id() -> None:
    store = InMemoryStore()
    rid = persist_identity(store, Identity("a", "A"))
    assert rid  # non-empty id