"""Telemetry layer: metrics, errors, throttle."""
from __future__ import annotations
from .metrics import MetricsSink, InMemoryMetricsSink, JSONLMetricsSink
from .errors import (
    TransientError,
    PermanentError,
    PolicyViolation,
    ContractBreach,
    UniversalMindError,
    Disposition,
    ErrorHandler,
)
from .throttle import ExecutionThrottle

__all__ = [
    'MetricsSink',
    'InMemoryMetricsSink',
    'JSONLMetricsSink',
    'TransientError',
    'PermanentError',
    'PolicyViolation',
    'ContractBreach',
    'UniversalMindError',
    'Disposition',
    'ErrorHandler',
    'ExecutionThrottle',
]