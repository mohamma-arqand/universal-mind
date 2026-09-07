"""Prometheus engine — the self-evolution loop, kept safe by construction.

The loop is: **observe** the ledger -> **measure** metrics -> **propose**
evolution actions -> **vet** them against a conservative policy -> **apply** a
property of the vetted proposals through a :class:`MutationApplier`.

Safety contract:

- The engine never writes to the ledger or to real files itself.
- By default the applier is :class:`NoopApplier`, which records the proposal
  as "proposals-only": the engine *surfaces* evolution but changes nothing.
- An :class:`InMemoryApplier` (for tests/demos) applies to a plain in-memory
  config dict, so the full apply/undo path can be exercised deterministically
  without ever touching real state.

All of this is deterministic: identical ledger state yields an identical
report (proposals, filters, and outcomes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from universal_mind.memory.store import MemoryStore

from .metrics import EvolutionMetrics, compute_metrics
from .policy import EvolutionPolicy
from .proposer import EvolutionProposal, PrometheusProposer

# The in-memory tuning surface the InMemoryApplier mutates. Keeping it as a
# small dict makes apply/undo trivially verifiable and free of side effects.
MutableConfig = dict[str, Any]


@runtime_checkable
class MutationApplier(Protocol):
    """A reversible mutator for ratified evolution proposals."""

    def apply(self, proposal: EvolutionProposal) -> str:
        """Apply the proposal and return a short outcome string."""
        ...

    def undo(self, proposal: EvolutionProposal) -> str:
        """Revert an applied proposal and return a short outcome string."""
        ...


class NoopApplier:
    """Default applier: surface the decision, change nothing.

    This is what makes self-evolution *safe by default* — running the loop
    produces a report a human can ratify, without mutating anything.
    """

    def apply(self, proposal: EvolutionProposal) -> str:
        return f"proposals-only: {proposal.kind.value} on {proposal.target} (await manual ratify)"

    def undo(self, proposal: EvolutionProposal) -> str:
        return f"nothing to undo for {proposal.kind.value} on {proposal.target}"


class InMemoryApplier:
    """Reversible applier over an in-memory config dict (tests/demos only)."""

    def __init__(self, config: MutableConfig | None = None) -> None:
        self.config: MutableConfig = {}
        if config is not None:
            self.config.update(config)
        self.applied: list[str] = []
        self.undone: list[str] = []

    def apply(self, proposal: EvolutionProposal) -> str:
        key = self._key(proposal)
        self.config[key] = proposal.suggested_change
        self.applied.append(proposal.kind.value)
        return f"applied {key}={proposal.suggested_change!r}"

    def undo(self, proposal: EvolutionProposal) -> str:
        key = self._key(proposal)
        was = self.config.pop(key, None)
        if was is not None:
            self.undone.append(proposal.kind.value)
        return f"undid {key} (was {was!r})" if was is not None else f"nothing for {key}"

    @staticmethod
    def _key(proposal: EvolutionProposal) -> str:
        return f"evolve:{proposal.kind.value}"


@dataclass(frozen=True)
class EvolutionReport:
    """The complete, auditable result of one evolution pass."""

    metrics: EvolutionMetrics
    proposals: tuple[EvolutionProposal, ...]
    applied: tuple[tuple[str, str], ...]  # (proposal_key, applier_outcome)
    rejected: tuple[tuple[EvolutionProposal, str], ...]  # (proposal, reason)
    summary: str

    @property
    def proposal_count(self) -> int:
        return len(self.proposals)

    @property
    def applied_count(self) -> int:
        return len(self.applied)


@runtime_checkable
class Prometheus(Protocol):
    """The self-evolution interface."""

    def evolve(self) -> EvolutionReport:
        """Run one observe->propose->vet->apply pass over the ledger."""
        ...


class InMemoryPrometheus:
    """Reference self-evolution engine over any :class:`MemoryStore`."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        policy: EvolutionPolicy | None = None,
        proposer: PrometheusProposer | None = None,
        applier: MutationApplier | None = None,
    ) -> None:
        self._store = store
        self._policy = policy if policy is not None else EvolutionPolicy()
        self._proposer = proposer if proposer is not None else PrometheusProposer()
        self._applier = applier if applier is not None else NoopApplier()

    def evolve(self) -> EvolutionReport:
        """Run one evolution pass (observe -> measure -> propose -> vet -> apply)."""
        records = list(self._store.read_all())
        metrics = compute_metrics(records)
        proposals = self._proposer.compose(metrics)
        allowed, rejected = self._policy.vet(proposals)

        applied: list[tuple[str, str]] = []
        for proposal in allowed:
            outcome = self._applier.apply(proposal)
            applied.append((proposal.kind.value, outcome))

        summary = (
            f"{len(proposals)} proposal(s): {len(applied)} applied, {len(rejected)} filtered"
            if applied or rejected or proposals
            else "no evolution proposals this pass"
        )
        return EvolutionReport(
            metrics=metrics,
            proposals=tuple(proposals),
            applied=tuple(applied),
            rejected=tuple(rejected),
            summary=summary,
        )