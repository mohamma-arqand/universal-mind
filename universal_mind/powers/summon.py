"""Summon power: spawn/attach an organ instance.

Spec concept: The ability to instantiate and attach a new organ (capability)
to the running system at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SummonInput:
    """Input for summoning an organ."""
    organ_name: str
    config: dict[str, Any]
    owner_id: str


@dataclass(frozen=True)
class SummonOutput:
    """Output from summoning an organ."""
    organ_id: str
    organ_name: str
    status: str  # "spawned" | "attached" | "failed"
    metadata: dict[str, Any]


@runtime_checkable
class Summon(Protocol):
    """Protocol for summoning organ instances.

    The Summon power allows the system to dynamically spawn or attach
    new organ instances at runtime, extending the system's capabilities.
    """

    async def summon(self, input: SummonInput) -> SummonOutput:
        """Spawn or attach an organ instance.

        Args:
            input: SummonInput with organ_name, config, and owner_id

        Returns:
            SummonOutput with organ_id, status, and metadata
        """
        ...


class InMemorySummon:
    """Reference in-memory implementation of Summon (no I/O)."""

    def __init__(self) -> None:
        self._organs: dict[str, dict[str, Any]] = {}
        self._counter = 0

    async def summon(self, input: SummonInput) -> SummonOutput:
        self._counter += 1
        organ_id = f"{input.organ_name}-{self._counter}"
        self._organs[organ_id] = {
            'name': input.organ_name,
            'config': input.config,
            'owner_id': input.owner_id,
            'status': 'spawned',
        }
        return SummonOutput(
            organ_id=organ_id,
            organ_name=input.organ_name,
            status='spawned',
            metadata={'config_keys': list(input.config.keys())},
        )