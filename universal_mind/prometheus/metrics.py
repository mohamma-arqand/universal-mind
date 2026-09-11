"""Prometheus metrics — evidence distilled from the memory ledger.

Observations (the "kind" fields that Prometheus reads) are written by the
ExecutiveMind and the FeedbackChannel into the same append-only store:

- ``capability_result``  payload: ``{"ok": bool, ...}``
- ``capability_selected``  payload: ``{"name": str, ...}``
- ``fault``  payload: ``{"fault_class": str, ...}``
- ``risk_assessment``  payload: ``{"risk_level": str, ...}``
- ``feedback``  payload: ``{"verdict": "approved"|"rejected"|"needs_work", ...}``

Each ``capability_result`` is attributed to the most recently selected
capability name (matches how the Executive sequences selection then result).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilitySignal:
    """Per-capability performance signal (all zero for a fresh name).

    Feedback verdicts are recorded against ledger *records*, not capabilities,
    so they are reported at :class:`EvolutionMetrics` level rather than here.
    """

    name: str
    executions: int = 0
    successes: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        """Fraction (0..1) of executions that succeeded; 1.0 when no runs yet."""
        if self.executions == 0:
            return 1.0
        return self.successes / self.executions


@dataclass(frozen=True)
class EvolutionMetrics:
    """Aggregated, deterministic snapshot of the ledger for evolution."""

    executions: int = 0
    successes: int = 0
    faults: int = 0
    feedback_approved: int = 0
    feedback_rejected: int = 0
    feedback_needs_work: int = 0
    counts_by_kind: dict[str, int] = field(default_factory=dict)
    fault_classes: dict[str, int] = field(default_factory=dict)
    risk_levels: dict[str, int] = field(default_factory=dict)
    capabilities: tuple[CapabilitySignal, ...] = field(default_factory=tuple)
    judgment_unhealthy: bool = False

    @property
    def error_rate(self) -> float:
        """Fraction (0..1) of executions that ended in a fault."""
        if self.executions == 0:
            return 0.0
        return self.faults / self.executions


def _bump(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def compute_metrics(records: list[dict[str, Any]]) -> EvolutionMetrics:
    """Derive an :class:`EvolutionMetrics` snapshot from raw ledger records.

    Deterministic and side-effect free: given the same ordered records, the
    same snapshot is produced.
    """
    executions = 0
    successes = 0
    faults = 0
    approved = 0
    rejected = 0
    needs_work = 0
    counts: dict[str, int] = {}
    fault_classes: dict[str, int] = {}
    risk_levels: dict[str, int] = {}
    signal_map: dict[str, CapabilitySignal] = {}
    order: list[str] = []
    last_selected = "unknown"
    judgment_unhealthy = False

    for record in records:
        kind = str(record.get("kind", ""))
        _bump(counts, kind)
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        if kind == "capability_selected":
            name = str(payload.get("name", "unknown"))
            last_selected = name
            if name not in signal_map:
                signal_map[name] = CapabilitySignal(name=name)
                order.append(name)
            continue

        if kind == "capability_result":
            executions += 1
            ok = bool(payload.get("ok", False))
            if ok:
                successes += 1
            if last_selected not in signal_map:
                signal_map[last_selected] = CapabilitySignal(name=last_selected)
                order.append(last_selected)
            current = signal_map[last_selected]
            signal_map[last_selected] = CapabilitySignal(
                name=current.name,
                executions=current.executions + 1,
                successes=current.successes + (1 if ok else 0),
                failures=current.failures + (0 if ok else 1),
            )
            continue

        if kind == "fault":
            faults += 1
            fault_class = str(payload.get("fault_class", "unknown"))
            _bump(fault_classes, fault_class)
            continue

        if kind == "risk_assessment":
            level = str(payload.get("risk_level", "unknown"))
            _bump(risk_levels, level)
            continue

        if kind == "feedback":
            verdict = str(payload.get("verdict", ""))
            if verdict == "approved":
                approved += 1
            elif verdict == "rejected":
                rejected += 1
            elif verdict == "needs_work":
                needs_work += 1
            continue

        if kind == "self_awareness":
            # The most recently recorded introspection pass marks judgment health.
            judgment_unhealthy = bool(payload.get("action_taken", False))
            continue

    capabilities = tuple(signal_map[name] for name in order)
    return EvolutionMetrics(
        executions=executions,
        successes=successes,
        faults=faults,
        feedback_approved=approved,
        feedback_rejected=rejected,
        feedback_needs_work=needs_work,
        counts_by_kind=counts,
        fault_classes=fault_classes,
        risk_levels=risk_levels,
        capabilities=capabilities,
        judgment_unhealthy=judgment_unhealthy,
    )