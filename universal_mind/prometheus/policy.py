"""Prometheus evolution policy — vets proposals before anything is applied.

The policy is the safety boundary on self-evolution. Following the rest of the
architecture (risk gates, ARELE veto logic), the default is conservative:

- ignore proposals with too few observations (avoid acting on noise);
- block HIGH-risk proposals by default;
- block irreversible proposals by default.

Anything that survives this gate is safe to *propose hardening*; application
remains a separate, gated, reversible action.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .proposer import EvolutionProposal, ProposalKind, Risk


@dataclass(frozen=True)
class EvolutionPolicy:
    """Conservative policy controlling which evolution proposals pass."""

    min_observations: int = 3
    max_risk: Risk = Risk.MEDIUM
    require_reversible: bool = True
    # Proposal kinds that are never auto-applied, however they score.
    blocked_kinds: frozenset[ProposalKind] = field(default_factory=frozenset)

    def allows(self, proposal: EvolutionProposal) -> bool:
        """Return True if the proposal is permitted by the policy."""
        if proposal.risk_rank > self._rank(self.max_risk):
            return False
        if self.require_reversible and not proposal.reversible:
            return False
        if proposal.kind in self.blocked_kinds:
            return False
        sample = int(proposal.evidence.get("executions", proposal.evidence.get("failures", 0)))
        return sample >= self.min_observations

    def reject_reason(self, proposal: EvolutionProposal) -> str | None:
        """Return a human-readable rejection reason, or None if allowed."""
        if proposal.risk_rank > self._rank(self.max_risk):
            return f"risk {proposal.risk.value} exceeds max {self.max_risk.value}"
        if self.require_reversible and not proposal.reversible:
            return "proposal is not reversible"
        if proposal.kind in self.blocked_kinds:
            return f"kind {proposal.kind.value} is blocked by policy"
        sample = int(proposal.evidence.get("executions", proposal.evidence.get("failures", 0)))
        if sample < self.min_observations:
            return f"only {sample} observations, below minimum {self.min_observations}"
        return None

    def vet(self, proposals: list[EvolutionProposal]) -> tuple[list[EvolutionProposal], list[tuple[EvolutionProposal, str]]]:
        """Partition proposals into (allowed, [(rejected, reason)])."""
        allowed: list[EvolutionProposal] = []
        rejected: list[tuple[EvolutionProposal, str]] = []
        for proposal in proposals:
            reason = self.reject_reason(proposal)
            if reason is None:
                allowed.append(proposal)
            else:
                rejected.append((proposal, reason))
        return allowed, rejected

    @staticmethod
    def _rank(risk: Risk) -> int:
        return _RISK_RANK[risk]


# Re-exported rank table for the policy module.
_RISK_RANK = {Risk.LOW: 0, Risk.MEDIUM: 1, Risk.HIGH: 2}