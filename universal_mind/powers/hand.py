"""Hand power: perform an external side effect.

Spec concept: The ability to execute actions that have side effects
in the external world (API calls, file writes, shell commands, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class HandInput:
    """Input for performing a side effect."""
    action: str  # e.g., "http_post", "shell_exec", "file_write"
    params: dict[str, Any]
    idempotency_key: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class HandOutput:
    """Output from performing a side effect."""
    success: bool
    result: Any
    error: str | None = None
    metadata: dict[str, Any] | None = None


@runtime_checkable
class Hand(Protocol):
    """Protocol for performing external side effects.

    The Hand power executes actions that mutate external state.
    All operations support dry_run mode and idempotency keys.
    """

    async def act(self, input: HandInput) -> HandOutput:
        """Perform an external side effect.

        Args:
            input: HandInput with action, params, optional idempotency_key and dry_run

        Returns:
            HandOutput with success, result, error, metadata
        """
        ...


class InMemoryHand:
    """Reference in-memory implementation of Hand (no I/O).

    Simulates side effects by recording them in memory.
    """

    def __init__(self) -> None:
        self._recorded_actions: list[HandInput] = []
        self._idempotency_keys: set[str] = set()

    async def act(self, input: HandInput) -> HandOutput:
        # Check idempotency
        if input.idempotency_key:
            if input.idempotency_key in self._idempotency_keys:
                return HandOutput(
                    success=True,
                    result={"status": "already_executed", "key": input.idempotency_key},
                    metadata={"idempotent": True},
                )
            self._idempotency_keys.add(input.idempotency_key)

        # Record the action
        self._recorded_actions.append(input)

        if input.dry_run:
            return HandOutput(
                success=True,
                result={"status": "dry_run", "action": input.action, "params": input.params},
                metadata={"dry_run": True},
            )

        # Simulate action execution
        if input.action == "http_post":
            return HandOutput(
                success=True,
                result={"status": "ok", "url": input.params.get("url"), "status_code": 200},
                metadata={"simulated": True},
            )
        elif input.action == "shell_exec":
            return HandOutput(
                success=True,
                result={"status": "ok", "argv": input.params.get("argv"), "exit_code": 0},
                metadata={"simulated": True},
            )
        elif input.action == "file_write":
            return HandOutput(
                success=True,
                result={"status": "ok", "path": input.params.get("path"), "bytes": len(str(input.params.get("content", "")))},
                metadata={"simulated": True},
            )
        else:
            return HandOutput(
                success=False,
                result=None,
                error=f"Unknown action: {input.action}",
                metadata={"simulated": True},
            )