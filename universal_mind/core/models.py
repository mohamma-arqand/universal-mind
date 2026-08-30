"""Shared dataclasses for ledger and execution results."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RecordStatus(str, Enum):
    """Classification for time-aware memory hits."""

    FRESH = 'fresh'
    STALE = 'stale'
    EXPIRED = 'expired'


@dataclass(frozen=True)
class LedgerRecord:
    """Normalized record structure stored in the ledger."""

    id: str
    owner_id: str
    kind: str
    created_at: str
    provenance: dict[str, Any]
    payload: Any
    schema_version: int = 1
    supersedes: str | None = None
    ttl_seconds: int | None = None


@dataclass(frozen=True)
class ExecutionRecord:
    """Outcome summary returned by the Executive Mind."""

    intent_record_id: str
    capability_record_id: str | None
    result_record_id: str | None
    fault_record_id: str | None
    status: str
    notes: tuple[str, ...] = field(default_factory=tuple)
