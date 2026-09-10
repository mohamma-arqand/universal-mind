"""Mnemosyne memory layer for auditing and recall."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.clock import Clock
from ..core.models import RecordStatus
from .store import MemoryStore


@dataclass(frozen=True)
class RecallHit:
    """A classified record returned by recall."""

    record: dict[str, Any]
    status: RecordStatus


@dataclass(frozen=True)
class QueryHit:
    """A record matched by *inferential* recall, with a relevance score."""

    record: dict[str, Any]
    score: float
    status: RecordStatus


def _tokens(text: str) -> set[str]:
    """Lowercased, minimal-length word tokens for lexical overlap."""
    return {t for t in text.lower().replace(",", " ").replace(".", " ").split() if len(t) > 2}


def _searchable_text(record: dict[str, Any]) -> str:
    """Concatenate the parts of a record that should match a query."""
    parts: list[str] = []
    kind = record.get("kind")
    if kind:
        parts.append(str(kind))
    provenance = record.get("provenance")
    if isinstance(provenance, dict):
        for value in provenance.values():
            parts.append(str(value))
    payload = record.get("payload")
    if isinstance(payload, dict):
        parts.append(str(payload.get("goal", "")))
        parts.append(str(payload.get("name", "")))
    else:
        parts.append(str(payload))
    return " ".join(parts)


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


class Mnemosyne:
    """Append-only memory service for recording and classifying facts."""

    def __init__(self, store: MemoryStore, clock: Clock) -> None:
        self.store = store
        self.clock = clock

    def record(
        self,
        *,
        owner_id: str,
        kind: str,
        payload: Any,
        provenance: dict[str, Any],
        supersedes: str | None = None,
        ttl_seconds: int | None = None,
        schema_version: int = 1,
        **extra: Any,
    ) -> str:
        """Append a ledger record with the required audit fields."""
        record = {
            'owner_id': owner_id,
            'kind': kind,
            'created_at': self.clock.now().isoformat(),
            'provenance': dict(provenance),
            'payload': payload,
            'schema_version': schema_version,
        }
        if supersedes is not None:
            record['supersedes'] = supersedes
        if ttl_seconds is not None:
            record['ttl_seconds'] = ttl_seconds
        record.update(extra)
        return self.store.append(record)

    def recall(self, *, owner_id: str, kind: str | None = None, target_record_id: str | None = None) -> list[RecallHit]:
        """Return matching records and classify them by age."""
        records = list(self.store.read_all())
        hits: list[RecallHit] = []
        for record in records:
            if record.get('owner_id') != owner_id:
                continue
            if kind is not None and record.get('kind') != kind:
                continue
            if target_record_id is not None and record.get('target_record_id') != target_record_id and record.get('payload', {}).get('target_record_id') != target_record_id:
                continue
            hits.append(RecallHit(record=record, status=self._classify(record)))
        return hits

    def query(
        self,
        text: str,
        *,
        owner_id: str | None = None,
        kinds: tuple[str, ...] | None = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> list[QueryHit]:
        """Inferential recall: rank records by lexical/kind relevance to ``text``.

        Each record is scored by overlapping the query tokens with the record's
        own searchable text (kind, citation/provenance string, and the
        stringified payload). Freshness is not decisive but is folded into the
        sort via the record's age classification: fresher-rankings beat older
        ones at equal relevance. Returns the top ``limit`` hits above
        ``min_score``, best first. This is what makes MNEMOSYNE a remembering
        substrate rather than a bare audit index.
        """
        query_tokens = _tokens(text)
        scored: list[tuple[float, QueryHit]] = []
        for record in self.store.read_all():
            if owner_id is not None and record.get("owner_id") != owner_id:
                continue
            if kinds is not None and record.get("kind") not in kinds:
                continue
            haystack = _searchable_text(record)
            hay_tokens = _tokens(haystack)
            if not hay_tokens:
                continue
            overlap = len(query_tokens & hay_tokens)
            precision = overlap / len(query_tokens) if query_tokens else 0.0
            # Freshness bonus keeps recency from being meaningless but never
            # overrides lexical relevance.
            status = self._classify(record)
            freshness = {RecordStatus.FRESH: 0.1, RecordStatus.STALE: 0.05, RecordStatus.EXPIRED: 0.0}[status]
            score = _clamp(precision + freshness)
            if score >= min_score:
                scored.append((score, QueryHit(record=record, score=round(score, 4), status=status)))
        scored.sort(key=lambda entry: (-entry[0], entry[1].record.get("created_at", "")))
        return [hit for _, hit in scored[:limit]]

    def _classify(self, record: dict[str, Any]) -> RecordStatus:
        created_at = datetime.fromisoformat(record['created_at'])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        ttl = record.get('ttl_seconds')
        if ttl is None:
            return RecordStatus.FRESH
        age = self.clock.now() - created_at
        if age <= timedelta(seconds=ttl):
            return RecordStatus.FRESH
        if age <= timedelta(seconds=ttl * 2):
            return RecordStatus.STALE
        return RecordStatus.EXPIRED

    def collect_expired(self) -> list[str]:
        """Remove expired records from the store and return their IDs.

        This method implements memory decay by permanently removing records
        that have exceeded their time-to-live threshold.
        """
        expired_ids = []
        for record in list(self.store.read_all()):
            if (
                self._classify(record) == RecordStatus.EXPIRED
                and self.store.delete(record['id'])
            ):
                expired_ids.append(record['id'])
        return expired_ids

    def decay(self, max_age: timedelta | None = None) -> int:
        """Decay memory by removing expired records.

        Args:
            max_age: Maximum age for records to keep. If None, uses TTL from records.

        Returns:
            Number of records removed.
        """
        count = 0
        for record in list(self.store.read_all()):
            if max_age:
                created_at = datetime.fromisoformat(record['created_at'])
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if (
                    self.clock.now() - created_at > max_age
                    and self.store.delete(record['id'])
                ):
                    count += 1
            else:
                if (
                    self._classify(record) == RecordStatus.EXPIRED
                    and self.store.delete(record['id'])
                ):
                    count += 1
        return count
