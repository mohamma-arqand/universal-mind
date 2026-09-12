"""Tests for Mnemosyne inferential recall (the `query` method)."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore


def _mnemosyne() -> Mnemosyne:
    store = InMemoryStore()
    return Mnemosyne(store, FrozenClock(datetime(2026, 1, 1, tzinfo=timezone.utc)))


def _record(
    m: Mnemosyne,
    *,
    owner: str = "owner",
    kind: str = "synthesis",
    goal: str = "write the monthly report",
    name: str = "report",
) -> str:
    return m.record(
        owner_id=owner,
        kind=kind,
        payload={"goal": goal, "name": name},
        provenance={"producer": "test", "owner_id": owner},
    )


def test_query_ranks_relevant_highest() -> None:
    m = _mnemosyne()
    _record(m, goal="summarize the security posture")
    _record(m, goal="write the monthly report")
    _record(m, kind="standard", goal="the standing standard", name="standard")

    hits = m.query("monthly report")
    assert hits, "query must return at least one hit"
    assert "monthly" in str(hits[0].record["payload"]["goal"])


def test_query_respects_kind_filter() -> None:
    m = _mnemosyne()
    _record(m, kind="synthesis", goal="write the report")
    _record(m, kind="standard", goal="the report benchmark", name="standard")
    hits = m.query("report", kinds=("standard",))
    assert hits
    assert all(h.record["kind"] == "standard" for h in hits)


def test_query_respects_owner_filter() -> None:
    m = _mnemosyne()
    _record(m, owner="alice", goal="alice write report")
    _record(m, owner="bob", goal="bob write report")
    hits = m.query("report", owner_id="alice")
    assert hits
    assert all(h.record["owner_id"] == "alice" for h in hits)


def test_query_min_score_filters_noise() -> None:
    m = _mnemosyne()
    _record(m, goal="write about unrelated tokens xyzzy")
    hits = m.query("completely absent query words", min_score=0.2)
    # The unrelated record should not match strongly; high min_score -> empty.
    assert all(h.score >= 0.2 for h in hits)


def test_query_returns_limited_results() -> None:
    m = _mnemosyne()
    for i in range(15):
        _record(m, goal=f"write report number {i}")
    hits = m.query("write report", limit=5)
    assert len(hits) <= 5


def test_query_scores_are_bounded() -> None:
    m = _mnemosyne()
    _record(m, goal="write the report")
    hits = m.query("write report")
    for h in hits:
        assert 0.0 <= h.score <= 1.0


def test_query_handles_empty_store() -> None:
    m = _mnemosyne()
    assert m.query("anything") == []


def test_empty_query_returns_nothing_not_every_fresh_record() -> None:
    """An empty/unparseable query has no signal; it must return [], not surface
    every fresh record via the freshness bonus (absence-as-success)."""
    m = _mnemosyne()
    _record(m, goal="write the report")
    _record(m, goal="summarize the posture")
    # a query with no substantive tokens (only <3-char words / punctuation)
    assert m.query("") == []
    assert m.query("a b") == []
    assert m.query(".. /") == []