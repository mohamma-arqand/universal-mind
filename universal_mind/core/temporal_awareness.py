"""Temporal awareness — what time is it, and what does that mean for the decision.

A clock gives the raw instant; a mind needs the *meaning* of the instant to act
well. This module is the temporal-awareness layer: from an injectable clock it
derives decision-relevant signals — business hours vs off-hours, weekday vs
weekend, and a freshness window — so a decision can be time-aware (e.g. "this is
an off-hours request, weigh it differently") rather than time-blind.

Deterministic given the clock: no wall-clock in the assertions, only in the
injected clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from universal_mind.core.clock import Clock


@dataclass(frozen=True)
class TemporalContext:
    """Time-derived signals that shape a decision."""

    isoweekday: int            # 1 (Mon) .. 7 (Sun)
    hour: int
    is_weekend: bool
    is_business_hours: bool    # 09:00–18:00, Mon–Fri
    freshness_hours: float     # age of ``reference`` in hours (0 if none)


def derive_temporal_context(
    clock: Clock,
    *,
    reference: datetime | None = None,
) -> TemporalContext:
    """Derive decision-relevant time signals from ``clock``.

    ``reference`` is an optional past instant (e.g. the last time a record was
    touched); when given, ``freshness_hours`` reports how old it is, so the mind
    can weigh stale vs fresh information.
    """
    now = clock.now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    weekday = now.isoweekday()
    hour = now.hour
    is_weekend = weekday >= 6
    is_business = (not is_weekend) and 9 <= hour < 18

    freshness = 0.0
    if reference is not None:
        ref = reference
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        freshness = max(0.0, (now - ref).total_seconds() / 3600.0)

    return TemporalContext(
        isoweekday=weekday,
        hour=hour,
        is_weekend=is_weekend,
        is_business_hours=is_business,
        freshness_hours=round(freshness, 4),
    )