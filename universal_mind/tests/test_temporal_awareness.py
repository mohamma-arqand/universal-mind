"""Tests for temporal awareness — time with meaning."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.core.clock import FrozenClock
from universal_mind.core.temporal_awareness import (
    derive_temporal_context,
)


def _clock(iso: str) -> FrozenClock:
    return FrozenClock(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc))


def test_business_hours_weekday() -> None:
    # Monday 2026-09-07 10:00 UTC
    ctx = derive_temporal_context(_clock("2026-09-07T10:00:00"))
    assert ctx.is_business_hours is True
    assert ctx.is_weekend is False
    assert ctx.isoweekday == 1


def test_off_hours_weekday() -> None:
    ctx = derive_temporal_context(_clock("2026-09-07T20:00:00"))
    assert ctx.is_business_hours is False
    assert ctx.is_weekend is False


def test_weekend_is_detected() -> None:
    # Sunday 2026-09-13
    ctx = derive_temporal_context(_clock("2026-09-13T10:00:00"))
    assert ctx.is_weekend is True
    assert ctx.is_business_hours is False


def test_freshness_is_computed_from_reference() -> None:
    reference = datetime.fromisoformat("2026-09-07T08:00:00").replace(tzinfo=timezone.utc)
    ctx = derive_temporal_context(_clock("2026-09-07T10:00:00"), reference=reference)
    assert abs(ctx.freshness_hours - 2.0) < 0.01


def test_no_reference_is_zero_freshness() -> None:
    ctx = derive_temporal_context(_clock("2026-09-07T10:00:00"))
    assert ctx.freshness_hours == 0.0


def test_context_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    c = derive_temporal_context(_clock("2026-09-07T10:00:00"))
    try:
        c.hour = 99  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True