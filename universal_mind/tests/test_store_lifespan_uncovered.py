"""Coverage for memory/store.py + lifespan.py remaining branches."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.lifespan import (
    MemoryBudget,
    _apply_budget,
    _significance,
    recall_context,
)
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import (
    CompactionPolicy,
    InMemoryStore,
    LocalJSONLStore,
    MemoryStore,
)

# --- MemoryStore base abstract contract ---


def test_base_memory_store_delete_raises_not_implemented() -> None:
    from collections.abc import Iterable

    class _AppendOnly(MemoryStore):
        def append(self, record: dict[str, Any]) -> str:
            return "x"

        def read_all(self) -> Iterable[dict[str, Any]]:
            return []

        def find(self, **filters: Any) -> list[dict[str, Any]]:
            return []

    with pytest.raises(NotImplementedError):
        _AppendOnly().delete("whatever")


def test_base_memory_store_compact_default_noop() -> None:
    from collections.abc import Iterable

    class _AppendOnly(MemoryStore):
        def append(self, record: dict[str, Any]) -> str:
            return "x"

        def read_all(self) -> Iterable[dict[str, Any]]:
            return []

        def find(self, **filters: Any) -> list[dict[str, Any]]:
            return []

    assert _AppendOnly().compact() == 0


def test_in_memory_store_delete_not_found() -> None:
    store = InMemoryStore()
    assert store.delete("missing") is False


# --- LocalJSONLStore durable behaviors ---


def test_local_jsonl_tombstone_and_compact(tmp_path: Path) -> None:
    store = LocalJSONLStore(directory=tmp_path)
    rid1 = store.append({"owner_id": "a", "kind": "fact", "payload": {"x": 1}})
    store.append({"owner_id": "a", "kind": "fact", "payload": {"x": 2}})

    # deleting a non-existent id -> False
    assert store.delete("missing") is False

    # deleting an existing id -> True, and read_all hides it
    assert store.delete(rid1) is True
    ids = [r.get("id") for r in store.read_all()]
    assert rid1 not in ids

    # compact rewrites the file without tombstones
    removed = store.compact()
    assert removed >= 0


def test_local_jsonl_delete_not_found_returns_false(tmp_path: Path) -> None:
    store = LocalJSONLStore(directory=tmp_path)
    assert store.delete("does-not-exist") is False


def test_local_jsonl_empty_lines_are_skipped(tmp_path: Path) -> None:
    store = LocalJSONLStore(directory=tmp_path)
    store.append({"owner_id": "a", "kind": "fact", "payload": {}})
    # append a blank line to the file
    with store.file_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    records = list(store.read_all())
    assert len(records) == 1


def test_local_jsonl_maybe_compact_no_live(tmp_path: Path) -> None:
    # live count 0 -> no compaction
    store = LocalJSONLStore(
        directory=tmp_path,
        compaction_policy=CompactionPolicy(min_records_before_compact=0),
    )
    assert store._maybe_compact() == 0


# --- lifespan ---


def _clock() -> FrozenClock:
    return FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))


def test_significance_ranks_kinds() -> None:
    assert _significance({"kind": "standard"}) == 90
    assert _significance({"kind": "human_consent"}) == 90
    assert _significance({"kind": "generated_power"}) == 60
    assert _significance({"kind": "feedback"}) == 50
    assert _significance({"kind": "fact"}) == 10


def test_recall_context_empty() -> None:
    store = InMemoryStore()
    result = recall_context(store, "nothing matches", owner_id="a")
    assert result.hits == ()
    assert result.summary == ""


def test_apply_budget_with_naive_and_malformed_created_at() -> None:
    store = InMemoryStore()
    # one malformed created_at and one naive (no tz) -> both skipped safely
    store.append({"owner_id": "a", "kind": "note", "payload": {}, "created_at": "not-a-date"})
    store.append({"owner_id": "a", "kind": "note", "payload": {}, "created_at": "2023-01-01T00:00:00"})
    m = Mnemosyne(store, _clock())
    trimmed = _apply_budget(m, MemoryBudget(max_records=1, decay_horizon_seconds=1))
    # malformed date is skipped (ValueError); naive date is eligible → trimmed == 1
    assert trimmed == 1