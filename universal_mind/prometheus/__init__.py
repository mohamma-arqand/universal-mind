"""PROMETHEUS — safe, evidence-backed self-evolution.

Observes the memory ledger, distills metrics, proposes evolution actions, vets
them against a conservative policy, and (with an explicit reversible applier)
applies them. Safe by default: the reference engine uses a :class:`NoopApplier`
and never mutates the ledger or real files on its own.
"""

from __future__ import annotations

from universal_mind.prometheus.apply import (
    ApplyOutcome,
    FallbackOrderApplier,
    apply_proposal,
    evolve_and_apply,
)
from universal_mind.prometheus.engine import (
    EvolutionReport,
    InMemoryApplier,
    InMemoryPrometheus,
    MutationApplier,
    NoopApplier,
    Prometheus,
    ThrottleApplier,
)
from universal_mind.prometheus.metrics import (
    CapabilitySignal,
    EvolutionMetrics,
    compute_metrics,
)
from universal_mind.prometheus.policy import EvolutionPolicy
from universal_mind.prometheus.proposer import (
    EvolutionProposal,
    PrometheusProposer,
    ProposalKind,
    Risk,
)

__all__ = [
    "ApplyOutcome",
    "CapabilitySignal",
    "EvolutionMetrics",
    "EvolutionPolicy",
    "EvolutionProposal",
    "EvolutionReport",
    "FallbackOrderApplier",
    "InMemoryApplier",
    "InMemoryPrometheus",
    "MutationApplier",
    "NoopApplier",
    "Prometheus",
    "PrometheusProposer",
    "ProposalKind",
    "Risk",
    "ThrottleApplier",
    "apply_proposal",
    "compute_metrics",
    "evolve_and_apply",
]