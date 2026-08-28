"""Identity objects for owners and tenants."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    """Represents a tenant or owner in the ledger."""

    owner_id: str
    display_name: str


DEFAULT_OWNER = Identity(owner_id='sovereign', display_name='Owner')
