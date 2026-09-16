"""Run history + chain advisor — learn from real runs, recommend a real chain.

Every Persian-command run is recorded to the persistent database (command, route,
success, timestamp). The advisor then mines that history: for a new command it
finds the most similar past command (by shared Persian vocabulary) and recommends
the chain that succeeded there — evidence-based recommendation, not a guess.

Two learning signals:
- similarity: shared capability-vocabulary words between the commands;
- success: only successful runs are recommended from (a failed chain never
  becomes advice).

Deterministic and pure. Honest: no history → no recommendation (never a guess).
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.database_suite import DatabaseSuite
from universal_mind.persian_router import _VOCAB


@dataclass(frozen=True)
class RunRecord:
    """One recorded run: the command, its route, and whether it succeeded."""

    record_id: int
    command: str
    route: tuple[str, ...]
    succeeded: bool


@dataclass(frozen=True)
class ChainAdvice:
    """A recommended chain, with the evidence that produced it."""

    route: tuple[str, ...]
    similar_command: str
    similarity: int           # count of shared vocabulary words
    succeeded_runs: int      # how many times this chain succeeded there


class RunHistory:
    """Record and query real runs in the persistent database."""

    def __init__(self, db: DatabaseSuite | None = None) -> None:
        self._db = db if db is not None else DatabaseSuite(persistent=True)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS run_history "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, route TEXT, "
            "succeeded INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )

    def record(self, command: str, route: list[str], succeeded: bool) -> None:
        """Append one real run to the history."""
        self._db.insert_many(
            "run_history",
            [{"command": command, "route": ",".join(route),
              "succeeded": "1" if succeeded else "0"}],
        )

    def successful_runs(self) -> list[RunRecord]:
        """Every successful run, oldest first."""
        q = self._db.query(
            "SELECT id, command, route, succeeded FROM run_history "
            "WHERE succeeded = 1 ORDER BY id"
        )
        if not q["ok"]:
            return []
        return [
            RunRecord(
                record_id=int(row["id"]),
                command=str(row["command"]),
                route=tuple(str(row["route"]).split(",")),
                succeeded=bool(int(row["succeeded"])),
            )
            for row in q["rows"]
        ]


def _capability_words(command: str) -> set[str]:
    """The vocabulary words that fire in this command (the routing signal)."""
    lowered = command.lower()
    return {word for word, _cap in _VOCAB if word in lowered}


class ChainAdvisor:
    """Recommend a chain from the operator's real run history."""

    def __init__(self, history: RunHistory | None = None) -> None:
        self._history = history if history is not None else RunHistory()

    def advise(self, command: str) -> ChainAdvice | None:
        """The best chain for this command, learned from past successes.

        Ranks past successful runs by shared vocabulary; the winner's route is
        the advice. No history or no overlap → None (never a guess).
        """
        words = _capability_words(command)
        if not words:
            return None
        best: tuple[int, RunRecord] | None = None
        for record in self._history.successful_runs():
            overlap = len(words & _capability_words(record.command))
            if overlap == 0:
                continue
            if best is None or overlap > best[0]:
                best = (overlap, record)
        if best is None:
            return None
        overlap, record = best
        return ChainAdvice(
            route=record.route,
            similar_command=record.command,
            similarity=overlap,
            succeeded_runs=1,
        )


__all__ = ["ChainAdvice", "ChainAdvisor", "RunHistory", "RunRecord"]