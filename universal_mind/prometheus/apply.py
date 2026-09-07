"""Evolution application layer — route vetted proposals to reversible appliers.

Prometheus *proposes*; this module *routes* each proposal to a reversible
applier that realizes it on the live executive, and refuses/ignores anything
unsupported. It reuses the in-module :class:`ThrottleApplier` for
:data:`ProposalKind.TIGHTEN_THROTTLE` and adds a :class:`FallbackOrderApplier`
for :data:`ProposalKind.REORDER_FALLBACK`, then composes everything behind a
single :func:`evolve_and_apply` entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.core.errors import ErrorHandler
from universal_mind.core.executive import ExecutiveMind
from universal_mind.memory.store import MemoryStore
from universal_mind.prometheus.engine import (
    EvolutionReport,
    InMemoryPrometheus,
    ThrottleApplier,
)
from universal_mind.prometheus.policy import EvolutionPolicy
from universal_mind.prometheus.proposer import EvolutionProposal, ProposalKind


class FallbackOrderApplier:
    """Reversible applier that realizes a REORDER_FALLBACK proposal.

    Installs a cheap, reliable fallback capability on the executive's
    ``ErrorHandler`` and records the prior chain so :meth:`undo` restores it
    exactly. Proposals of any other kind are ignored.
    """

    def __init__(self, error_handler: ErrorHandler, fallback: str = "echo") -> None:
        self._error_handler = error_handler
        self._fallback = fallback
        self._prior: dict[str, Any] = {}

    def apply(self, proposal: EvolutionProposal) -> str:
        if proposal.kind != ProposalKind.REORDER_FALLBACK:
            return f"ignored: {proposal.kind.value} is not a fallback proposal"
        old = self._error_handler.fallback_capability
        self._prior[proposal.kind.value] = old
        self._error_handler.fallback_capability = [self._fallback]
        return f"installed fallback chain [{self._fallback}] (was {old!r})"

    def undo(self, proposal: EvolutionProposal) -> str:
        key = proposal.kind.value
        if key in self._prior:
            self._error_handler.fallback_capability = self._prior.pop(key)
            return f"restored fallback chain to {self._error_handler.fallback_capability!r}"
        return f"nothing to undo for {key}"


@dataclass(frozen=True)
class ApplyOutcome:
    """One proposal's application/refusal result."""

    kind: ProposalKind
    detail: str


def apply_proposal(
    proposal: EvolutionProposal,
    throttle: ThrottleApplier,
    fallback: FallbackOrderApplier,
) -> ApplyOutcome:
    """Route a single proposal to the matching reversible applier (or ignore)."""
    if proposal.kind == ProposalKind.TIGHTEN_THROTTLE:
        return ApplyOutcome(kind=proposal.kind, detail=throttle.apply(proposal))
    if proposal.kind == ProposalKind.REORDER_FALLBACK:
        return ApplyOutcome(kind=proposal.kind, detail=fallback.apply(proposal))
    return ApplyOutcome(kind=proposal.kind, detail=f"ignored: unsupported kind {proposal.kind.value}")


def evolve_and_apply(
    store: MemoryStore,
    executive: ExecutiveMind,
    *,
    policy: EvolutionPolicy | None = None,
    throttle: ThrottleApplier | None = None,
    fallback: FallbackOrderApplier | None = None,
) -> tuple[EvolutionReport, list[ApplyOutcome]]:
    """Run one Prometheus pass and realize each vetted proposal on the executive.

    Composes :class:`InMemoryPrometheus` with reversible appliers (the default
    throttle applier wraps ``executive.throttle``; the default fallback applier
    wraps ``executive.error_handler``). Everything is deterministic and
    reversible; unsupported proposal kinds are reported as ignored, mutating
    nothing.

    Returns ``(report, outcomes)``.
    """
    effective_throttle = throttle if throttle is not None else ThrottleApplier(executive.throttle)
    effective_fallback = fallback if fallback is not None else FallbackOrderApplier(executive.error_handler)
    report = InMemoryPrometheus(store, policy=policy).evolve()
    outcomes = [
        apply_proposal(proposal, effective_throttle, effective_fallback)
        for proposal in report.proposals
    ]
    return report, outcomes