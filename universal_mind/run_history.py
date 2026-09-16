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
            "succeeded INTEGER, excellence REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        # Migrate an existing persistent DB in place (add excellence if missing).
        try:
            cols = self._db.query(
                "SELECT name FROM pragma_table_info('run_history')"
            )
            if cols.get("ok") and "excellence" not in {str(c["name"]) for c in cols.get("rows", [])}:
                self._db.execute("ALTER TABLE run_history ADD COLUMN excellence REAL")
        except Exception as exc:  # noqa: BLE001 — migration is best-effort, never fatal
            import sys

            print(f"[history] مهاجرت ستون excellence ناموفق بود: {exc}", file=sys.stderr)

    def record(self, command: str, route: list[str], succeeded: bool, excellence: float | None = None) -> None:
        """Append one real run to the history (with its ARETĒ excellence)."""
        self._db.insert_many(
            "run_history",
            [{"command": command, "route": ",".join(route),
              "succeeded": "1" if succeeded else "0",
              "excellence": "" if excellence is None else f"{excellence:.4f}"}],
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

        Candidates come from BOTH real sources of evidence: the recorded run
        history AND the operator's saved chains (a saved chain is an explicit
        trust signal — it counts as one win). Ranked by (vocabulary overlap,
        times succeeded); no history and no overlap → None (never a guess).
        """
        words = _capability_words(command)
        if not words:
            return None
        # route -> (best overlap, success count, representative command)
        candidates: dict[tuple[str, ...], tuple[int, int, str]] = {}
        for record in self._history.successful_runs():
            overlap = len(words & _capability_words(record.command))
            if overlap == 0:
                continue
            route = record.route
            prev = candidates.get(route)
            if prev is None:
                candidates[route] = (overlap, 1, record.command)
            else:
                candidates[route] = (
                    max(prev[0], overlap),
                    prev[1] + 1,
                    record.command if overlap >= prev[0] else prev[2],
                )
        # Saved chains are explicit operator trust: each becomes a candidate
        # with its own overlap (a saved chain counts as one recorded win).
        try:
            from universal_mind.chains_store import ChainsStore

            for chain in ChainsStore().load():
                overlap = len(words & _capability_words(chain.name))
                if overlap == 0:
                    continue
                route = tuple(chain.capabilities)
                prev = candidates.get(route)
                if prev is None:
                    candidates[route] = (overlap, 1, chain.name)
                elif overlap > prev[0]:
                    candidates[route] = (overlap, prev[1] + 1, chain.name)
        except Exception:  # noqa: BLE001 — the store is a bonus source, never fatal
            pass

        if not candidates:
            return None
        # Rank: overlap first, then success count (the learned winning record).
        route, (overlap, wins, command) = max(
            candidates.items(), key=lambda item: (item[1][0], item[1][1])
        )
        return ChainAdvice(
            route=route,
            similar_command=command,
            similarity=overlap,
            succeeded_runs=wins,
        )


__all__ = ["ChainAdvice", "ChainAdvisor", "RunHistory", "RunRecord"]