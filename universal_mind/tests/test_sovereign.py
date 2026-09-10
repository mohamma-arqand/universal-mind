"""Tests for the sovereign context — a continuous self distilled from the ledger."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.core.clock import FrozenClock
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore
from universal_mind.sovereign import (
    build_sovereign_context,
    inject_preamble,
)


def _clock() -> FrozenClock:
    return FrozenClock(datetime(2026, 1, 1, tzinfo=timezone.utc))


def _store_with_history() -> InMemoryStore:
    store = InMemoryStore()
    m = Mnemosyne(store, _clock())
    m.record(owner_id="o", kind="standard", payload={"name": "report-2", "promotion_depth": 2}, provenance={"p": "x"})
    m.record(owner_id="o", kind="synthesis", payload={"goal": "write"}, provenance={"p": "x"})
    m.record(owner_id="o", kind="human_consent", payload={"verdict": "consent"}, provenance={"p": "x"})
    return store


def test_build_context_reads_current_standard() -> None:
    ctx = build_sovereign_context(_store_with_history())
    assert ctx.current_standard == "report-2"
    assert ctx.lineage_depth == 2


def test_context_collects_experience_kinds() -> None:
    ctx = build_sovereign_context(_store_with_history())
    assert "standard" in ctx.experience
    assert "synthesis" in ctx.experience
    assert "human_consent" in ctx.experience


def test_empty_store_has_identity_line_only() -> None:
    ctx = build_sovereign_context(InMemoryStore())
    assert ctx.current_standard is None
    assert ctx.lineage_depth == 0
    assert ctx.experience == ()
    assert "no standing standard" in ctx.summary


def test_summary_is_stable_and_deterministic() -> None:
    a = build_sovereign_context(_store_with_history())
    b = build_sovereign_context(_store_with_history())
    assert a.summary == b.summary


def test_inject_preamble_prepends_identity() -> None:
    ctx = build_sovereign_context(_store_with_history())
    out = inject_preamble("summarize the report", ctx)
    assert out.startswith("ONE MIND")
    assert "summarize the report" in out
    assert out.endswith("summarize the report")


def test_inject_preamble_is_deterministic() -> None:
    ctx = build_sovereign_context(_store_with_history())
    assert inject_preamble("do the thing", ctx) == inject_preamble("do the thing", ctx)


def test_context_lines_up_with_identity() -> None:
    ctx = build_sovereign_context(_store_with_history())
    assert ctx.identity_line == "ONE MIND · MANY MINDS · ONE INTEGRATED JUDGMENT"


def test_inject_preamble_keeps_goal_parseable() -> None:
    """The preamble is context, not the goal itself."""
    ctx = build_sovereign_context(_store_with_history())
    out = inject_preamble("write and review", ctx)
    # The final words are the user's actual goal.
    assert out.rstrip().split()[-2:] == ["and", "review"]