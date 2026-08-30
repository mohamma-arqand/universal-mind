"""Recording protocols for execution observability.

Event recording is a side-channel: it must never alter control flow in the
caller. Records are timestamped from an injected :class:`~universal_mind.core.clock.Clock`
so tests can be deterministic — never from ``time.time()`` or ``datetime.now()``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from universal_mind.core.clock import Clock

# Explicit upper bound for a :class:`MemoryRecorder` built in *production*
# code. An unbounded recorder ("maxlen=None" in a shipped path) silently grows
# without limit, so non-test construction sites MUST pass this cap (or use
# :func:`make_bounded_recorder`) rather than rely on the unbounded default.
# Enforcement is structural, not advisory: the AST gate in
# :mod:`tests.test_recorder_injection` fails any non-test file that constructs
# ``MemoryRecorder(...)`` without an explicit ``maxlen=`` argument. Tests are
# free to construct unbounded recorders for inspection purposes.
DEFAULT_RECORDER_MAXLEN = 1024


def make_bounded_recorder(
    clock: Clock, *, maxlen: int = DEFAULT_RECORDER_MAXLEN,
) -> MemoryRecorder:
    """Blessed construction path for a recorder in production code.

    Always applies an explicit bounded ``maxlen`` (default
    :data:`DEFAULT_RECORDER_MAXLEN`), so a production recorder cannot silently
    grow without limit. The structural AST gate accepts this call because it
    passes ``maxlen=`` explicitly; a bare ``MemoryRecorder(clock=...)`` in a
    non-test file is rejected instead. Tests that need an unbounded recorder
    build ``MemoryRecorder`` directly with ``maxlen=None``.
    """
    return MemoryRecorder(clock=clock, maxlen=maxlen)


@runtime_checkable
class Recorder(Protocol):
    """Protocol for execution event recorders.

    Implementations receive a single ``event`` name plus arbitrary structured
    ``fields``. Methods must be total: any conforming product and any conforming
    test double satisfies this protocol.
    """

    def record(self, event: str, /, **fields: object) -> None:
        """Record one event. Must never raise into the caller."""
        ...


class NullRecorder:
    """No-op recorder. Records nothing, holds no state."""

    def record(self, event: str, /, **fields: object) -> None:
        return None


@dataclass
class MemoryRecorder:
    """Records events into a read-only container for inspection in tests.

    Each entry carries the ``event`` name, the recorded ``fields``, and the
    wall-clock :attr:`at` taken from the injected :class:`Clock` — never from
    ``time.time()`` / ``datetime.now()``.

    When ``maxlen`` is given, the container becomes a bounded ``deque(maxlen=...)``
    ring buffer and :attr:`dropped_events` counts the events evicted by overflow.
    ``None`` (the default) reproduces the unbounded behaviour and always reports
    ``dropped_events == 0``. Production code should prefer
    :func:`make_bounded_recorder`, which forces an explicit bound.
    """

    clock: Clock
    maxlen: int | None = None
    _events: deque[RecordedEvent] = field(default_factory=deque, init=False)
    dropped_events: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.maxlen is not None:
            self._events = deque(maxlen=self.maxlen)

    def record(self, event: str, /, **fields: object) -> None:
        ev = RecordedEvent(event=event, fields=fields, at=self.clock.now())
        # Ring buffer at capacity: the append will evict the head, so count it.
        if self.maxlen is not None and len(self._events) == self.maxlen:
            self.dropped_events += 1
        self._events.append(ev)

    @property
    def events(self) -> tuple[RecordedEvent, ...]:
        """Read-only snapshot of recorded events (never a live reference)."""
        return tuple(self._events)

    @property
    def last(self) -> RecordedEvent | None:
        """The most recently recorded event, or ``None`` if nothing recorded."""
        return self._events[-1] if self._events else None


@dataclass(frozen=True)
class RecordedEvent:
    """A single recorded execution event."""

    event: str
    fields: dict[str, object]
    at: datetime