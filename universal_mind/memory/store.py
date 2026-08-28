"""Memory store abstractions and concrete append-only backends."""
from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import uuid
from typing import Any, Iterable

from ..core.models import LedgerRecord


@dataclass(frozen=True)
class CompactionPolicy:
    """Policy for automatic compaction of tombstone records.
    
    max_tombstone_ratio: Trigger compaction when tombstones / live_records > this ratio.
    min_records_before_compact: Minimum total records before compaction is considered.
    max_tombstones: Trigger compaction when absolute tombstone count >= this value.
        Set to 0 to disable absolute count trigger.
    """
    max_tombstone_ratio: float = 0.3
    min_records_before_compact: int = 100
    max_tombstones: int = 500


class MemoryStore(ABC):
    """Append-only persistence contract for ledger records."""

    @abstractmethod
    def append(self, record: dict[str, Any]) -> str:
        """Append a record and return its id."""

    @abstractmethod
    def read_all(self) -> Iterable[dict[str, Any]]:
        """Yield all persisted records in append order."""

    @abstractmethod
    def find(self, **filters: Any) -> list[dict[str, Any]]:
        """Return records that match the provided top-level filters."""

    def delete(self, record_id: str) -> bool:
        """Delete a record by id if supported.

        Default implementation raises NotImplementedError for append-only stores.
        Override in subclasses that support deletion (e.g., InMemoryStore).
        Subclasses that cannot support deletion should raise NotImplementedError
        rather than silently no-op, so callers are not misled into believing a
        delete succeeded when it did not.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support delete(). "
            "Override in a subclass or use a store implementation that supports deletion."
        )

    def compact(self) -> int:
        """Physically remove deleted/tombstoned records and return the count removed.

        Optional; the default is a no-op returning 0. Backends that support
        deletion of persistent data (e.g. LocalJSONLStore) override this.
        """
        return 0


class InMemoryStore(MemoryStore):
    """Simple in-memory backend used for tests and demos."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> str:
        record = deepcopy(record)
        record.setdefault('id', uuid.uuid4().hex)
        self._records.append(record)
        return str(record['id'])

    def read_all(self) -> Iterable[dict[str, Any]]:
        return [deepcopy(record) for record in self._records]

    def find(self, **filters: Any) -> list[dict[str, Any]]:
        result = []
        for record in self._records:
            if all(record.get(key) == value for key, value in filters.items()):
                result.append(deepcopy(record))
        return result

    def delete(self, record_id: str) -> bool:
        """Delete a record by id. Returns True if deleted, False if not found."""
        for i, record in enumerate(self._records):
            if record.get('id') == record_id:
                self._records.pop(i)
                return True
        return False


class LocalJSONLStore(MemoryStore):
    """Append-only JSON Lines store under a configurable directory.
    
    Deletion is implemented via tombstone records (kind='tombstone') that reference
    the deleted record's ID. The read_all() method filters out tombstoned records.
    
    Automatic compaction: after each delete(), if the ratio of tombstones to live
    records exceeds the policy threshold, compaction is triggered synchronously.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        filename: str = 'ledger.jsonl',
        compaction_policy: CompactionPolicy | None = None,
    ) -> None:
        self.directory = Path(directory).expanduser() if directory is not None else Path.home() / '.universal_mind'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file_path = self.directory / filename
        self.file_path.touch(exist_ok=True)
        self.compaction_policy = compaction_policy or CompactionPolicy()
        self._live_count: int = 0
        self._tombstone_count: int = 0
        self._counts_initialized: bool = False

    def _refresh_counts(self) -> None:
        """Scan the file and count live records and tombstones."""
        if self._counts_initialized:
            return
        live = 0
        tombstones = 0
        if self.file_path.exists():
            with self.file_path.open('r', encoding='utf-8') as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    if record.get('kind') == 'tombstone':
                        tombstones += 1
                    else:
                        live += 1
        self._live_count = live
        self._tombstone_count = tombstones
        self._counts_initialized = True

    def _maybe_compact(self) -> int:
        """Check policy and trigger compaction if threshold exceeded.
        
        Returns the number of records removed, or 0 if no compaction occurred.
        """
        self._refresh_counts()
        total = self._live_count + self._tombstone_count
        if total < self.compaction_policy.min_records_before_compact:
            return 0
        if self._live_count == 0:
            return 0
        ratio = self._tombstone_count / self._live_count
        ratio_triggered = ratio > self.compaction_policy.max_tombstone_ratio
        count_triggered = (
            self.compaction_policy.max_tombstones > 0
            and self._tombstone_count >= self.compaction_policy.max_tombstones
        )
        if ratio_triggered or count_triggered:
            return self.compact()
        return 0

    def append(self, record: dict[str, Any]) -> str:
        record = deepcopy(record)
        record.setdefault('id', uuid.uuid4().hex)
        with self.file_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
        self._live_count += 1
        return str(record['id'])

    def read_all(self) -> Iterable[dict[str, Any]]:
        """Return all non-tombstoned records in append order."""
        records: list[dict[str, Any]] = []
        tombstoned_ids: set[str] = set()
        
        with self.file_path.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get('kind') == 'tombstone':
                    # Tombstone record: {'kind': 'tombstone', 'target_record_id': '...', ...}
                    target_id = record.get('target_record_id') or record.get('payload', {}).get('target_record_id')
                    if target_id:
                        tombstoned_ids.add(target_id)
                else:
                    records.append(record)
        
        # Filter out tombstoned records
        return [r for r in records if r.get('id') not in tombstoned_ids]

    def find(self, **filters: Any) -> list[dict[str, Any]]:
        result = []
        for record in self.read_all():
            if all(record.get(key) == value for key, value in filters.items()):
                result.append(record)
        return result

    def delete(self, record_id: str) -> bool:
        """Write a tombstone record to mark the target as deleted.
        
        Returns True if the record existed (tombstone written), False if not found.
        Triggers automatic compaction if the tombstone ratio exceeds the policy.
        """
        # First check if the record exists
        self._refresh_counts()
        exists = False
        for record in self.read_all():
            if record.get('id') == record_id:
                exists = True
                break
        
        if not exists:
            return False
        
        # Write tombstone record
        tombstone = {
            'id': uuid.uuid4().hex,
            'owner_id': 'system',
            'kind': 'tombstone',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'provenance': {'producer': 'LocalJSONLStore.delete'},
            'payload': {'target_record_id': record_id},
            'schema_version': 1,
            'target_record_id': record_id,
        }
        with self.file_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(tombstone, ensure_ascii=False, sort_keys=True) + '\n')
        
        self._tombstone_count += 1
        
        # Trigger automatic compaction if policy threshold exceeded
        self._maybe_compact()
        
        return True

    def compact(self) -> int:
        """Rewrite the file dropping tombstoned records and the tombstone markers.

        Reads every line, collects the set of tombstoned target ids, then rewrites
        the file containing only live, non-tombstone records. Returns the number of
        lines (records + tombstones) dropped from the file.
        
        Crash-safe: writes to a temp file, fsyncs, then atomically replaces.
        """
        tombstoned_ids: set[str] = set()
        live_records: list[dict[str, Any]] = []

        with self.file_path.open('r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get('kind') == 'tombstone':
                    target_id = record.get('target_record_id') or record.get('payload', {}).get('target_record_id')
                    if target_id:
                        tombstoned_ids.add(target_id)
                else:
                    live_records.append(record)

        kept = [r for r in live_records if r.get('id') not in tombstoned_ids]
        removed = len(live_records) + len(tombstoned_ids) - len(kept)

        # Crash-safe atomic replace: write to temp file, fsync, then replace
        temp_path = self.file_path.with_suffix('.jsonl.tmp')
        with temp_path.open('w', encoding='utf-8') as handle:
            for record in kept:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        
        # Atomic replace
        os.replace(temp_path, self.file_path)
        
        # Update counts
        self._live_count = len(kept)
        self._tombstone_count = 0
        
        return removed
