"""Prometheus proposer — derives candidate evolution actions from metrics.

Every proposal is *evidence-linked* (carries the signal that motivated it) and
is tagged with a risk level and a reversibility flag so that :class:`~universal_mind.prometheus.policy.EvolutionPolicy`
can vet it before anything is applied. Producing a proposal never mutates
state; application is a separate, gated step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .metrics import CapabilitySignal, EvolutionMetrics


class ProposalKind(str, Enum):
    """The kinds of evolution action Prometheus can suggest."""

    TIGHTEN_THROTTLE = "tighten_throttle"
    REVIEW_CAPABILITY = "review_capability"
    REORDER_FALLBACK = "reorder_fallback"
    RESPECT_VETO = "respect_veto"
    CHAMPION = "champion"
    SELF_CORRECT = "self_correct"


class Risk(str, Enum):
    """Evolution proposal risk tiers (strictly ordered)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_RISK_RANK = {Risk.LOW: 0, Risk.MEDIUM: 1, Risk.HIGH: 2}


@dataclass(frozen=True)
class EvolutionProposal:
    """A candidate self-evolution action with its supporting evidence."""

    kind: ProposalKind
    target: str
    reason: str
    risk: Risk
    reversible: bool
    suggested_change: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def risk_rank(self) -> int:
        """Numeric risk rank for policy comparison (low=0)."""
        return _RISK_RANK[self.risk]


def _signal(sig: CapabilitySignal) -> dict[str, Any]:
    return {
        "name": sig.name,
        "executions": sig.executions,
        "successes": sig.successes,
        "success_rate": sig.success_rate,
    }


class PrometheusProposer:
    """Deterministic rule set that turns metrics into proposals.

    The thresholds are deliberately modest and conservative; the point of the
    proposer is to surface *evidence-backed* suggestions, not to act on them.
    """

    def __init__(
        self,
        *,
        low_success_threshold: float = 0.5,
        sample_window: int = 3,
        high_error_rate: float = 0.4,
        promote_threshold: float = 0.8,
    ) -> None:
        self._low_success = low_success_threshold
        self._sample = sample_window
        self._high_error = high_error_rate
        self._promote = promote_threshold

    def compose(self, metrics: EvolutionMetrics) -> list[EvolutionProposal]:
        """Return proposed evolution actions for the snapshot (no side effects)."""
        proposals: list[EvolutionProposal] = []

        if metrics.executions >= self._sample and metrics.error_rate > self._high_error:
            proposals.append(
                EvolutionProposal(
                    kind=ProposalKind.TIGHTEN_THROTTLE,
                    target="executive.throttle",
                    reason=(
                        f"error_rate {metrics.error_rate:.2f} exceeds "
                        f"{self._high_error:.2f} over {metrics.executions} executions"
                    ),
                    risk=Risk.LOW,
                    reversible=True,
                    suggested_change="lower ExecutionThrottle.error_rate_threshold",
                    evidence={
                        "executions": metrics.executions,
                        "faults": metrics.faults,
                        "error_rate": metrics.error_rate,
                    },
                )
            )

        # Human feedback is recorded against ledger records, so it is reasoned
        # about at the ledger level (not per capability).
        if metrics.feedback_rejected > 0:
            proposals.append(
                EvolutionProposal(
                    kind=ProposalKind.RESPECT_VETO,
                    target="executive.feedback",
                    reason=f"human feedback carries {metrics.feedback_rejected} rejection(s)",
                    risk=Risk.LOW,
                    reversible=True,
                    suggested_change="honor the human verdict (do not re-run rejected intents)",
                    evidence={
                        "rejections": metrics.feedback_rejected,
                        "executions": metrics.executions,
                    },
                )
            )

        # A self-awareness pass that found the mind judging unhealthily prompts a
        # concrete self-correction: tighten the acceptance bar / budget. This is the
        # bridge between judgment health and the Prometheus evolution loop.
        if metrics.judgment_unhealthy:
            proposals.append(
                EvolutionProposal(
                    kind=ProposalKind.SELF_CORRECT,
                    target="executive.self_awareness",
                    reason="judgment health reported unhealthy — the mind is drifting",
                    risk=Risk.LOW,
                    reversible=True,
                    suggested_change="raise acceptance bar / tighten execution budget",
                    evidence={
                        "judgment_unhealthy": True,
                        "executions": metrics.executions,
                    },
                )
            )

        for sig in metrics.capabilities:
            evidence = _signal(sig)
            if (
                sig.executions >= self._sample
                and sig.success_rate < self._low_success
            ):
                proposals.append(
                    EvolutionProposal(
                        kind=ProposalKind.REVIEW_CAPABILITY,
                        target=sig.name,
                        reason=(
                            f"{sig.name} success rate {sig.success_rate:.2f} is below "
                            f"{self._low_success:.2f} over {sig.executions} runs"
                        ),
                        risk=Risk.MEDIUM,
                        reversible=True,
                        suggested_change=f"flag {sig.name} for review / demote priority",
                        evidence=evidence,
                    )
                )
            if sig.failures >= self._sample:
                proposals.append(
                    EvolutionProposal(
                        kind=ProposalKind.REORDER_FALLBACK,
                        target=sig.name,
                        reason=f"{sig.name} has {sig.failures} failures across {sig.executions} runs",
                        risk=Risk.LOW,
                        reversible=True,
                        suggested_change="advance a lower-cost fallback in the chain",
                        evidence=evidence,
                    )
                )
            if (
                sig.success_rate >= self._promote
                and sig.executions >= self._sample
            ):
                proposals.append(
                    EvolutionProposal(
                        kind=ProposalKind.CHAMPION,
                        target=sig.name,
                        reason=(
                            f"{sig.name} is reliable ({sig.success_rate:.2f}) over "
                            f"{sig.executions} runs"
                        ),
                        risk=Risk.LOW,
                        reversible=True,
                        suggested_change="keep / raise priority of a proven capability",
                        evidence=evidence,
                    )
                )

        return proposals