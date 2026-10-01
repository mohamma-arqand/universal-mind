"""Custom chains — the operator's own multi-capability sequences, saved for real.

The chain tab ships six preset chains; this module gives the operator the power to
build their OWN: pick capabilities in order, name it, and store it in the
PERSISTENT database (~/.universal-mind/mind.db). A saved chain survives restarts
and appears alongside the presets — the operator's workflow becomes first-class
data, not a hardcoded list.

Deterministic and local: the store is the same real SQLite engine every other
suite uses. A saved chain is validated at load time — a chain naming a capability
that no longer exists is skipped honestly (never executed blindly).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from universal_mind.real_tool_registry import _REAL_CONNECTORS
from universal_mind.tool_registry import ToolRegistry

if TYPE_CHECKING:  # R59 P6: the annotation-only import — the runtime import
    from universal_mind.database_suite import DatabaseSuite  # noqa: F401


@dataclass(frozen=True)
class SavedChain:
    """One operator-defined chain: a name and an ordered capability list."""

    name: str
    capabilities: tuple[str, ...]
    chain_id: int


class ChainsStore:
    """Save/load the operator's custom chains in the persistent SQLite database."""

    def __init__(self, registry: ToolRegistry | None = None,
                 db: DatabaseSuite | None = None) -> None:
        from universal_mind.database_suite import DatabaseSuite as _DS

        # R59 P6: an INJECTABLE store — the same pattern every other store
        # takes. Tests must never touch the operator's real mind.db: before
        # this, __init__ built DatabaseSuite(persistent=True) directly and no
        # patch could isolate it (a test leaked two rows into the real store;
        # they were found and removed with a named cleanup).
        self._db = db if db is not None else _DS(persistent=True)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS custom_chains "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, capabilities TEXT)"
        )
        self._registry = registry if registry is not None else ToolRegistry()

    def save(self, name: str, capabilities: list[str]) -> SavedChain:
        """Store a new custom chain for real (with a unique name)."""
        if not name.strip():
            raise ValueError("chain name must be non-empty")
        if not capabilities:
            raise ValueError("chain needs at least one capability")
        unknown = [c for c in capabilities if c not in _REAL_CONNECTORS]
        if unknown:
            raise ValueError(f"unknown capabilities: {', '.join(unknown)}")
        # Replace an existing chain with the same name (an update, not a duplicate).
        existing = self.load()
        for chain in existing:
            if chain.name == name.strip():
                self.delete(chain.chain_id)
                break
        stored = self._db.insert_many(
            "custom_chains", [{"name": name.strip(), "capabilities": ",".join(capabilities)}]
        )
        if not stored["ok"]:
            raise RuntimeError(stored["error"])
        saved = next((c for c in self.load() if c.name == name.strip()), None)
        if saved is None:
            raise RuntimeError("chain was not persisted")
        return saved

    def load(self) -> list[SavedChain]:
        """Load every saved chain, validating each against the real registry.

        A chain naming a capability that is no longer registered is skipped
        honestly (it is data from an older session, not an executable plan).
        """
        query = self._db.query("SELECT id, name, capabilities FROM custom_chains ORDER BY id")
        if not query["ok"]:
            return []
        chains: list[SavedChain] = []
        for row in query["rows"]:
            caps = [c.strip() for c in str(row["capabilities"]).split(",") if c.strip()]
            known = [c for c in caps if c in _REAL_CONNECTORS]
            if not known:
                continue  # nothing executable left in this chain
            chains.append(
                SavedChain(
                    name=str(row["name"]),
                    capabilities=tuple(known),
                    chain_id=int(row["id"]),
                )
            )
        return chains

    def delete(self, chain_id: int) -> bool:
        """Remove a saved chain for real."""
        out = self._db.execute(f"DELETE FROM custom_chains WHERE id = {int(chain_id)}")
        return bool(out["ok"])


__all__ = ["ChainsStore", "SavedChain"]