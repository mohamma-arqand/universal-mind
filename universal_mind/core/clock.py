"""Clock abstraction used for all time-sensitive behavior."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


class Clock(ABC):
    """Abstract clock returning aware UTC datetimes."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC time."""


class SystemClock(Clock):
    """Clock backed by the host system time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FrozenClock(Clock):
    """Clock fixed at a chosen UTC instant for tests."""

    current: datetime

    def __post_init__(self) -> None:
        if self.current.tzinfo is None:
            object.__setattr__(self, 'current', self.current.replace(tzinfo=timezone.utc))

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> FrozenClock:
        """Return a new frozen clock advanced by seconds."""
        return FrozenClock(self.current + timedelta(seconds=seconds))
