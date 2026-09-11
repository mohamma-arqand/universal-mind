"""Observability: execution event recording.

Provides a runtime-checkable :class:`Recorder` protocol plus two conforming
implementations (:class:`NullRecorder` and :class:`MemoryRecorder`). This
package must not import ``core.executive`` to avoid a circular import; the
wire-up is one-directional (executive -> recorder).
"""

from __future__ import annotations

from .metrics import (
    DeployMetrics,
    deploy_metrics_from_store,
    derive_deploy_metrics,
)
from .recorder import (
    DEFAULT_RECORDER_MAXLEN,
    MemoryRecorder,
    NullRecorder,
    RecordedEvent,
    Recorder,
    make_bounded_recorder,
)

__all__ = [
    "DEFAULT_RECORDER_MAXLEN",
    "DeployMetrics",
    "MemoryRecorder",
    "NullRecorder",
    "RecordedEvent",
    "Recorder",
    "deploy_metrics_from_store",
    "derive_deploy_metrics",
    "make_bounded_recorder",
]