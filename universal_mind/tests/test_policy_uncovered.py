"""Coverage + behavior tests for the Prometheus evolution policy."""

from __future__ import annotations

from typing import Any

from universal_mind.prometheus.policy import EvolutionPolicy
from universal_mind.prometheus.proposer import (
    EvolutionProposal,
    ProposalKind,
    Risk,
)


def _proposal(
    kind: ProposalKind = ProposalKind.TIGHTEN_THROTTLE,
    risk: Risk = Risk.LOW,
    reversible: bool = True,
    evidence: dict[str, Any] | None = None,
) -> EvolutionProposal:
    return EvolutionProposal(
        kind=kind,
        target="executive.throttle",
        reason="test",
        risk=risk,
        reversible=reversible,
        suggested_change="x",
        evidence=evidence if evidence is not None else {"executions": 10},
    )


def test_policy_allows_low_risk_sufficient_observations() -> None:
    p = EvolutionPolicy(min_observations=3)
    assert p.allows(_proposal(evidence={"executions": 5})) is True


def test_policy_blocks_high_risk() -> None:
    p = EvolutionPolicy(max_risk=Risk.MEDIUM)
    assert p.allows(_proposal(risk=Risk.HIGH)) is False


def test_policy_blocks_irreversible() -> None:
    p = EvolutionPolicy(require_reversible=True)
    assert p.allows(_proposal(reversible=False)) is False


def test_policy_blocks_blocked_kind() -> None:
    p = EvolutionPolicy(blocked_kinds=frozenset({ProposalKind.CHAMPION}))
    assert p.allows(_proposal(kind=ProposalKind.CHAMPION)) is False
    # allowed kind unaffected
    assert p.allows(_proposal(kind=ProposalKind.TIGHTEN_THROTTLE)) is True


def test_policy_blocks_insufficient_observations() -> None:
    p = EvolutionPolicy(min_observations=10)
    assert p.allows(_proposal(evidence={"executions": 2})) is False


def test_reject_reason_for_each_branch() -> None:
    p = EvolutionPolicy(min_observations=3, blocked_kinds=frozenset({ProposalKind.CHAMPION}))
    assert p.reject_reason(_proposal(risk=Risk.HIGH)) is not None
    assert p.reject_reason(_proposal(reversible=False)) is not None
    assert p.reject_reason(_proposal(kind=ProposalKind.CHAMPION)) is not None
    assert p.reject_reason(_proposal(evidence={"executions": 1})) is not None
    assert p.reject_reason(_proposal(evidence={"executions": 10})) is None


def test_reject_reason_matches_allows() -> None:
    """reject_reason is None exactly when allows() is True (no divergence)."""
    p = EvolutionPolicy(min_observations=3)
    cases = [
        _proposal(evidence={"executions": 5}),
        _proposal(risk=Risk.HIGH),
        _proposal(reversible=False),
        _proposal(evidence={"executions": 1}),
    ]
    for proposal in cases:
        allowed = p.allows(proposal)
        reason = p.reject_reason(proposal)
        assert (reason is None) == allowed


def test_vet_partitions() -> None:
    p = EvolutionPolicy(min_observations=3)
    proposals = [
        _proposal(evidence={"executions": 5}),
        _proposal(risk=Risk.HIGH),
        _proposal(evidence={"executions": 1}),
    ]
    allowed, rejected = p.vet(proposals)
    assert len(allowed) == 1
    assert len(rejected) == 2