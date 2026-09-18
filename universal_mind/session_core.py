"""SessionCore — one shared context for the whole platform run.

The platform's three faces (tick, CLI, window) each open their own
connections today; a SESSION is the missing level above them: one place that
counts what THIS sitting did (runs, verdicts, flows, repairs) and lets any
face read the same live numbers. The dashboard's «داوری نشست» becomes a
live counter instead of a re-query; the tick can report the sitting it just
did (not just the history it wrote).

Honest rules:
- The core is a process-level singleton keyed by a session id stamped at
  first import (or explicitly opened) — one sitting, one core.
- Counters are ATOMIC increments (add_*), never recomputed from scratch:
  what was counted cannot be retro-fitted.
- Snapshot is a frozen dict — reading it never mutates it.
- No persistence: a session lives exactly as long as the process that owns
  it. What must survive is written to the real history; the session is the
  IN-MEMORY now.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SessionSnapshot:
    """An immutable read of the session's counters."""

    session_id: str
    started_at: str
    runs: int
    ok_runs: int
    flows: int
    repairs: int
    judged: int
    goals_started: int
    goals_finished: int


class SessionCore:
    """The process-wide session context (thread-safe by one small lock)."""

    _instance: "SessionCore | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session_id = uuid.uuid4().hex[:12]
        self._started_at = datetime.now().isoformat(timespec="seconds")
        self._counters: dict[str, int] = {k: 0 for k in (
            "runs", "ok_runs", "flows", "repairs", "judged",
            "goals_started", "goals_finished",
        )}

    # -- singleton --------------------------------------------------------
    @classmethod
    def current(cls) -> "SessionCore":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> "SessionCore":
        """A fresh session (tests and explicit new-sittings only)."""
        with cls._instance_lock:
            cls._instance = SessionCore()
        return cls._instance

    # -- mutation --------------------------------------------------------
    def add(self, kind: str, amount: int = 1) -> None:
        """Atomic increment of one counter (unknown counters are refused)."""
        with self._lock:
            if kind not in self._counters:
                raise KeyError(f"شمارندهی نشست ناشناخته: {kind}")
            self._counters[kind] += amount

    # -- reading ---------------------------------------------------------
    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def started_at(self) -> str:
        return self._started_at

    def snapshot(self) -> SessionSnapshot:
        """The frozen now — reading never mutates."""
        with self._lock:
            return SessionSnapshot(
                session_id=self._session_id,
                started_at=self._started_at,
                **dict(self._counters),
            )

    def report(self) -> str:
        """The sitting rendered as fluent Persian."""
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        s = self.snapshot()
        lines = [
            f"🪪 نشست {s.session_id} (از {s.started_at.translate(fa)})",
            f"• اجراها: {str(s.runs).translate(fa)}"
            f" | موفق: {str(s.ok_runs).translate(fa)}",
            f"• جریانهای سنتز: {str(s.flows).translate(fa)} | ترمیمها: {str(s.repairs).translate(fa)}",
            f"• داوریها: {str(s.judged).translate(fa)}",
            f"• هدفها: {str(s.goals_started).translate(fa)} آغاز / "
            f"{str(s.goals_finished).translate(fa)} پایان",
        ]
        return "\n".join(lines)


__all__ = ["SessionCore", "SessionSnapshot"]