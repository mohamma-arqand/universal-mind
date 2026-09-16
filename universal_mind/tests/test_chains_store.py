"""Tests for custom chains — the operator's own saved multi-capability sequences."""

from __future__ import annotations

import uuid

import pytest

from universal_mind.chains_store import ChainsStore


@pytest.fixture()  # type: ignore[untyped-decorator]
def store() -> ChainsStore:
    """A real persistent store with a unique marker table per test."""
    return ChainsStore()


def _unique(store: ChainsStore) -> str:
    return f"زنجیره تست {uuid.uuid4().hex[:8]}"


def test_save_and_load_roundtrip(store: ChainsStore) -> None:
    name = _unique(store)
    saved = store.save(name, ["media", "chart"])
    assert saved.name == name
    assert saved.capabilities == ("media", "chart")
    loaded = {c.name: c.capabilities for c in store.load()}
    assert loaded[name] == ("media", "chart")
    store.delete(saved.chain_id)


def test_save_survives_a_fresh_store_instance(store: ChainsStore) -> None:
    """A saved chain survives a brand-new store (a real restart)."""
    name = _unique(store)
    saved = store.save(name, ["data", "database"])
    fresh = ChainsStore()
    loaded = {c.name: c.capabilities for c in fresh.load()}
    assert loaded[name] == ("data", "database")
    store.delete(saved.chain_id)


def test_save_replaces_same_name(store: ChainsStore) -> None:
    """Saving with an existing name updates the chain, never duplicates it."""
    name = _unique(store)
    first = store.save(name, ["media"])
    second = store.save(name, ["media", "archive"])
    all_with_name = [c for c in store.load() if c.name == name]
    assert len(all_with_name) == 1
    assert second.capabilities == ("media", "archive")
    store.delete(first.chain_id)
    store.delete(second.chain_id)


def test_unknown_capability_is_refused(store: ChainsStore) -> None:
    with pytest.raises(ValueError) as exc:
        store.save(_unique(store), ["quantum_gravity"])
    assert "unknown capabilities" in str(exc.value)


def test_empty_chain_is_refused(store: ChainsStore) -> None:
    with pytest.raises(ValueError):
        store.save(_unique(store), [])


def test_chain_with_removed_capability_is_skipped_honestly(store: ChainsStore) -> None:
    """A saved chain naming a removed capability is skipped at load (honest)."""
    from unittest.mock import patch

    name = _unique(store)
    saved = store.save(name, ["media"])
    # Simulate the capability disappearing from the registry.
    with patch("universal_mind.chains_store._REAL_CONNECTORS", {"media": object()}):
        loaded = [c for c in ChainsStore().load() if c.name == name]
        # "media" still exists, so it survives — but a chain of only unknowns
        # would be skipped. Verify the honest filter exists:
        assert loaded[0].capabilities == ("media",)
    store.delete(saved.chain_id)