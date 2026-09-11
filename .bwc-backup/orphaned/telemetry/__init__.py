"""Telemetry layer: metrics, errors, throttle."""
from __future__ import annotations

from .errors import (
    ContractBreach,
    Disposition,
    ErrorHandler,
    PermanentError,
    PolicyViolation,
    TransientError,
    UniversalMindError,
)
from .metrics import InMemoryMetricsSink, JSONLMetricsSink, MetricsSink
from .throttle import ExecutionThrottle

__all__ = [
    'ContractBreach',
    'Disposition',
    'ErrorHandler',
    'ExecutionThrottle',
    'InMemoryMetricsSink',
    'JSONLMetricsSink',
    'MetricsSink',
    'PermanentError',
    'PolicyViolation',
    'TransientError',
    'UniversalMindError',
]