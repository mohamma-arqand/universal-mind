"""Tests for distributed memory — several instances, one synchronized ledger."""

from __future__ import annotations

from pathlib import Path

from universal_mind.memory.shared import (
    SharedLedger,
    append_through,
    is_synchronized,
    open_shared_ledger,
)


def test_two_instances_are_synchronized(tmp_path: Path) -> None:
    a, b = open_shared_ledger(str(tmp_path))
    append_through(a, "alice", "note", {"x": 1})
    # The write through 'a' is immediately visible through 'b'.
    assert is_synchronized([a, b]) is True
    assert len(list(b.read_all())) == 1


def test_write_through_b_visible_to_a(tmp_path: Path) -> None:
    a, b = open_shared_ledger(str(tmp_path))
    append_through(b, "bob", "note", {"x": 2})
    kinds = [r.get("kind") for r in a.read_all()]
    assert "note" in kinds


def test_three_instances_converge(tmp_path: Path) -> None:
    handles = open_shared_ledger(str(tmp_path), instances=3)
    append_through(handles[0], "alice", "n1", {})
    append_through(handles[1], "bob", "n2", {})
    assert is_synchronized(handles) is True
    assert len(list(handles[2].read_all())) == 2


def test_shared_ledger_dataclass_is_frozen(tmp_path: Path) -> None:
    from dataclasses import FrozenInstanceError

    sl = SharedLedger(directory=tmp_path)
    try:
        sl.filename = "x"  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True