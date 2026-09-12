"""Tests for the action audit trail (super-platform Phase 5b)."""

from __future__ import annotations

from universal_mind.audit_trail import AuditTrail


def test_record_and_replay() -> None:
    trail = AuditTrail()
    trail.record("transcode", "ffmpeg", {"input": "in.mp4"}, "transcoded.mp4", ok=True)
    entries = trail.entries()
    assert len(entries) == 1
    assert entries[0].capability == "transcode"
    assert entries[0].output == "transcoded.mp4"


def test_trace_filters_by_capability() -> None:
    trail = AuditTrail()
    trail.record("a", "ta", None, 1, True)
    trail.record("b", "tb", None, 2, True)
    trail.record("a", "tc", None, 3, False, "boom")
    a_entries = trail.trace("a")
    assert len(a_entries) == 2
    assert all(e.capability == "a" for e in a_entries)


def test_last_returns_most_recent() -> None:
    trail = AuditTrail()
    trail.record("a", "t", None, 1, True)
    trail.record("b", "t", None, 2, True)
    assert trail.last() is not None
    assert trail.last().capability == "b"


def test_failure_entry_carries_error() -> None:
    trail = AuditTrail()
    trail.record("x", "t", None, None, ok=False, error="timeout")
    entry = trail.last()
    assert entry is not None
    assert entry.ok is False
    assert entry.error == "timeout"


def test_entries_are_frozen() -> None:
    from dataclasses import FrozenInstanceError

    trail = AuditTrail()
    trail.record("a", "t", None, 1, True)
    entry = trail.entries()[0]
    try:
        entry.output = "mutated"  # type: ignore[misc]
        mutated = True
    except FrozenInstanceError:
        mutated = False
    assert mutated is False