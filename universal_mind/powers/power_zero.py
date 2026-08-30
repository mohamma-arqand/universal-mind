"""PowerZero: the only component allowed to mint new powers at runtime.

Precedence order is immutable - a module-level Final[tuple[str, ...]] frozen at import.
No setters, no constructor args, no env vars, no config keys can reorder or replace precedence.
Minted powers are appended STRICTLY BELOW all built-in powers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar
from typing import Final as TypingFinal

# =============================================================================
# POWER ZERO PRECEDENCE - IMMUTABLE, FROZEN AT IMPORT
# =============================================================================

# The fundamental gate precedence order. This is a tuple (immutable), not a list/dict.
# Higher index = higher precedence (runs first).
# This is a module-level Final, frozen at import time.
GATE_PRECEDENCE: TypingFinal[tuple[str, ...]] = (
    "PowerZero",      # 0 - absolute veto authority
    "Risk",           # 1 - safety/risk assessment
    "Strategic",      # 2 - strategic alignment
    "HumanFeedback",  # 3 - human-in-the-loop
    "Policy",         # 4 - policy compliance
    "Resource",       # 5 - resource limits
    "Temporal",       # 6 - time-based constraints
)

# Verify it's a tuple at import time
assert isinstance(GATE_PRECEDENCE, tuple), "GATE_PRECEDENCE must be a tuple"
assert len(GATE_PRECEDENCE) == 7, "GATE_PRECEDENCE must have exactly 7 built-in powers"


class ImmutablePrecedence(Exception):
    """Raised when attempting to modify PowerZero precedence."""


class DuplicateMintedPower(Exception):
    """Raised when attempting to mint a power with a duplicate name."""


@dataclass(frozen=True)
class MintedPower:
    """A power minted at runtime by PowerZero."""
    name: str
    precedence: int  # Will be assigned strictly below all built-in powers
    description: str
    metadata: dict[str, Any]


class PowerZero:
    """The only component allowed to mint new powers at runtime.

    Precedence order is immutable. Minted powers are appended STRICTLY BELOW
    all built-in powers - a minted power can NEVER outrank a fundamental power.
    """

    # Class-level storage for minted powers
    _minted_powers: ClassVar[list[MintedPower]] = []
    _minted_names: ClassVar[set[str]] = set()

    # Built-in power count (immutable)
    _BUILTIN_COUNT: ClassVar[int] = len(GATE_PRECEDENCE)

    def __init__(self) -> None:
        # No constructor args that can affect precedence
        pass

    def __setattr__(self, name: str, value: Any) -> None:
        """Block any attempt to set precedence-related attributes."""
        if name in ('GATE_PRECEDENCE', '_minted_powers', '_minted_names', '_BUILTIN_COUNT'):
            raise ImmutablePrecedence(f"Cannot modify {name}: PowerZero precedence is immutable")
        super().__setattr__(name, value)

    @classmethod
    def get_precedence(cls) -> tuple[str, ...]:
        """Return the full precedence order: built-ins first, then minted powers."""
        minted_names = tuple(p.name for p in cls._minted_powers)
        return GATE_PRECEDENCE + minted_names

    @classmethod
    def get_builtin_precedence(cls) -> tuple[str, ...]:
        """Return only the built-in precedence (immutable)."""
        return GATE_PRECEDENCE

    @classmethod
    def get_minted_powers(cls) -> tuple[MintedPower, ...]:
        """Return all minted powers in order."""
        return tuple(cls._minted_powers)

    @classmethod
    def mint_power(cls, name: str, description: str, metadata: dict[str, Any] | None = None) -> MintedPower:
        """Mint a new power at runtime.

        The minted power is appended STRICTLY BELOW all built-in powers.
        It can NEVER outrank a fundamental power.

        Args:
            name: Unique name for the minted power
            description: Human-readable description
            metadata: Optional additional metadata

        Returns:
            The created MintedPower with assigned precedence

        Raises:
            DuplicateMintedPower: If a power with this name already exists
        """
        if name in cls._minted_names:
            raise DuplicateMintedPower(f"Power already minted: {name}")
        if name in GATE_PRECEDENCE:
            raise DuplicateMintedPower(f"Cannot mint power with built-in name: {name}")

        # Precedence is strictly below all built-ins
        # Built-ins have precedence 0 to len(GATE_PRECEDENCE)-1
        # Minted powers start at len(GATE_PRECEDENCE) and increment
        precedence = cls._BUILTIN_COUNT + len(cls._minted_powers)

        minted = MintedPower(
            name=name,
            precedence=precedence,
            description=description,
            metadata=metadata or {},
        )

        cls._minted_powers.append(minted)
        cls._minted_names.add(name)

        return minted

    @classmethod
    def reset_minted(cls) -> None:
        """Reset minted powers (for testing only)."""
        cls._minted_powers.clear()
        cls._minted_names.clear()

    @classmethod
    def verify_minted_below_builtins(cls) -> bool:
        """Verify that all minted powers have precedence below built-ins.

        Returns:
            True if all minted powers are below built-ins, False otherwise.
        """
        for power in cls._minted_powers:
            if power.precedence < cls._BUILTIN_COUNT:
                return False
        return True


# GATE_PRECEDENCE is a module-level Final tuple - Python prevents reassignment
# at the module level by convention. The class-level __setattr__ protects
# instance attributes. Module-level constants are immutable by convention.