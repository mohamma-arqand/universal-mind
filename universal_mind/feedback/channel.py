"""Feedback ingestion and aggregation over the same ledger."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..core.clock import Clock
from ..memory.mnemosyne import Mnemosyne
from ..memory.store import MemoryStore


class Verdict(str, Enum):
    """Human feedback verdicts."""

    APPROVED = 'approved'
    REJECTED = 'rejected'
    NEEDS_WORK = 'needs_work'


@dataclass(frozen=True)
class FeedbackPolicy:
    """Policy that gates execution based on historical human feedback."""
    
    rejection_threshold: int = 1
    needs_work_threshold: int = 2
    approval_threshold: int = 1
    
    def should_block(self, aggregation: dict[str, int]) -> bool:
        """Determine whether execution should be blocked for a target.
        
        A target is blocked if rejections exceed the threshold, or if
        repeated needs_work feedback reaches the threshold without approval.
        """
        if aggregation[Verdict.REJECTED.value] >= self.rejection_threshold:
            return True
        return (
            aggregation[Verdict.NEEDS_WORK.value] >= self.needs_work_threshold
            and aggregation[Verdict.APPROVED.value] < self.approval_threshold
        )


@dataclass(frozen=True)
class HumanFeedbackGate:
    """Provides a gate on execution based on human feedback history."""

    store: MemoryStore
    clock: Clock
    policy: FeedbackPolicy = FeedbackPolicy()
    
    def submit(self, owner_id: str, target_record_id: str, verdict: Verdict, note: str) -> str:
        """Persist a feedback record for a target record."""
        return FeedbackChannel(self.store, self.clock).submit(owner_id, target_record_id, verdict, note)
    
    def for_target(self, target_record_id: str) -> list[dict[str, Any]]:
        """Return all feedback records attached to a target record."""
        return FeedbackChannel(self.store, self.clock).for_target(target_record_id)
    
    def aggregate(self, target_record_id: str) -> dict[str, int]:
        """Count feedback verdicts for a specific target record."""
        return FeedbackChannel(self.store, self.clock).aggregate(target_record_id)
    
    def is_blocked(self, target_record_id: str) -> bool:
        """Return True if execution on the target should be blocked by feedback."""
        return self.policy.should_block(self.aggregate(target_record_id))


@dataclass(frozen=True)
class FeedbackChannel:
    """Append-only channel for annotating execution records."""

    store: MemoryStore
    clock: Clock

    def submit(self, owner_id: str, target_record_id: str, verdict: Verdict, note: str) -> str:
        """Persist a feedback record for a target record."""
        mnemosyne = Mnemosyne(self.store, self.clock)
        return mnemosyne.record(
            owner_id=owner_id,
            kind='feedback',
            payload={'target_record_id': target_record_id, 'verdict': verdict.value, 'note': note},
            provenance={'producer': 'FeedbackChannel'},
            target_record_id=target_record_id,
            verdict=verdict.value,
            note=note,
        )

    def for_target(self, target_record_id: str) -> list[dict[str, Any]]:
        """Return all feedback records attached to a target record."""
        return [record for record in self.store.read_all() if record.get('kind') == 'feedback' and (record.get('target_record_id') == target_record_id or record.get('payload', {}).get('target_record_id') == target_record_id)]

    def aggregate(self, target_record_id: str) -> dict[str, int]:
        """Count feedback verdicts for a specific target record."""
        counts = Counter(record.get('payload', {}).get('verdict') for record in self.for_target(target_record_id))
        return {
            Verdict.APPROVED.value: counts.get(Verdict.APPROVED.value, 0),
            Verdict.REJECTED.value: counts.get(Verdict.REJECTED.value, 0),
            Verdict.NEEDS_WORK.value: counts.get(Verdict.NEEDS_WORK.value, 0),
        }


def feedback_gate(store: MemoryStore, clock: Clock, policy: FeedbackPolicy | None = None) -> HumanFeedbackGate:
    """Factory for creating a HumanFeedbackGate."""
    return HumanFeedbackGate(store=store, clock=clock, policy=policy or FeedbackPolicy())
