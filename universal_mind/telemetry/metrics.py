"""Metrics sink abstractions for telemetry."""
from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MetricEvent:
    """A single metric event."""
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'labels': self.labels,
            'timestamp': self.timestamp.isoformat(),
        }


class MetricsSink(ABC):
    """Abstract sink for metric events."""
    
    @abstractmethod
    def emit(self, event: MetricEvent) -> None:
        """Emit a metric event."""
        ...
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered events."""
        ...


class InMemoryMetricsSink(MetricsSink):
    """In-memory metrics sink for testing."""
    
    def __init__(self) -> None:
        self._events: list[MetricEvent] = []
        self._lock = threading.Lock()
    
    def emit(self, event: MetricEvent) -> None:
        with self._lock:
            self._events.append(event)
    
    def flush(self) -> None:
        pass  # No-op for in-memory
    
    def get_events(self) -> list[MetricEvent]:
        with self._lock:
            return list(self._events)
    
    def get_latest(self, name: str) -> MetricEvent | None:
        with self._lock:
            for event in reversed(self._events):
                if event.name == name:
                    return event
            return None


class JSONLMetricsSink(MetricsSink):
    """JSON Lines metrics sink for persistent storage."""
    
    def __init__(self, directory: str | Path, filename: str = 'metrics.jsonl') -> None:
        self.directory = Path(directory).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file_path = self.directory / filename
        self._lock = threading.Lock()
    
    def emit(self, event: MetricEvent) -> None:
        with self._lock, self.file_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + '\n')
    
    def flush(self) -> None:
        pass  # Line-by-line, no buffering