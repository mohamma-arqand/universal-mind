"""
PowerZero precedence gate - absolute veto authority.

Order (immutable): PowerZero -> Risk -> Strategic -> HumanFeedback

PowerZero.veto(intent) -> bool
If True: no other gates run, nothing can override.

Fail-closed: one DENY is enough. DEFER beats ALLOW.
Output: IntegratedJudgment(decision, chain: list[(gate, verdict, reason)])
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Protocol, Callable
from universal_mind.core.intent import Intent
from universal_mind.pantheon.registry import CapabilityDossier


class Verdict(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"


class GateName(Enum):
    POWER_ZERO = "PowerZero"
    RISK = "Risk"
    STRATEGIC = "Strategic"
    HUMAN_FEEDBACK = "HumanFeedback"


@dataclass(frozen=True)
class GateResult:
    gate: GateName
    verdict: Verdict
    reason: str


@dataclass(frozen=True)
class IntegratedJudgment:
    decision: Verdict
    chain: List[GateResult]

    @property
    def allowed(self) -> bool:
        return self.decision == Verdict.ALLOW


class PowerZero(Protocol):
    """PowerZero gate - absolute veto authority."""

    def veto(self, intent: Intent) -> bool:
        """
        Returns True if the intent is absolutely vetoed.
        If True: no other gates execute, nothing can override.
        """
        ...


class RiskGate(Protocol):
    """Risk assessment gate."""

    def assess(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        ...


class StrategicGate(Protocol):
    """Strategic gate."""

    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        ...


class HumanFeedbackGate(Protocol):
    """Human feedback gate."""

    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        ...


# Immutable gate order - cannot be changed from outside
_GATE_ORDER: tuple[GateName, ...] = (
    GateName.POWER_ZERO,
    GateName.RISK,
    GateName.STRATEGIC,
    GateName.HUMAN_FEEDBACK,
)


def get_gate_order() -> tuple[GateName, ...]:
    """Return the immutable gate order."""
    return _GATE_ORDER


def _combine_verdicts(verdicts: List[Verdict]) -> Verdict:
    """Combine verdicts: one DENY = DENY, DEFER beats ALLOW, else ALLOW."""
    if Verdict.DENY in verdicts:
        return Verdict.DENY
    if Verdict.DEFER in verdicts:
        return Verdict.DEFER
    return Verdict.ALLOW


class PrecedencePipeline:
    """
    Immutable precedence pipeline for gate evaluation.

    Order: PowerZero -> Risk -> Strategic -> HumanFeedback
    - PowerZero veto stops everything (absolute)
    - Fail-closed: one DENY = DENY
    - DEFER beats ALLOW
    """

    def __init__(
        self,
        power_zero: PowerZero,
        risk_gate: RiskGate,
        strategic_gate: StrategicGate,
        human_feedback_gate: HumanFeedbackGate,
    ):
        self._power_zero = power_zero
        self._risk_gate = risk_gate
        self._strategic_gate = strategic_gate
        self._human_feedback_gate = human_feedback_gate

    def evaluate(self, intent: Intent, capability: CapabilityDossier) -> IntegratedJudgment:
        """Evaluate all gates in precedence order."""
        chain: List[GateResult] = []

        # 1. PowerZero - absolute veto
        if self._power_zero.veto(intent):
            chain.append(GateResult(GateName.POWER_ZERO, Verdict.DENY, "PowerZero veto"))
            return IntegratedJudgment(Verdict.DENY, chain)

        chain.append(GateResult(GateName.POWER_ZERO, Verdict.ALLOW, "PowerZero passed"))

        # 2. Risk gate
        risk_verdict = self._risk_gate.assess(intent, capability)
        chain.append(GateResult(GateName.RISK, risk_verdict, f"Risk: {risk_verdict.value}"))
        if risk_verdict == Verdict.DENY:
            return IntegratedJudgment(Verdict.DENY, chain)

        # 3. Strategic gate
        strategic_verdict = self._strategic_gate.decide(intent, capability)
        chain.append(GateResult(GateName.STRATEGIC, strategic_verdict, f"Strategic: {strategic_verdict.value}"))
        if strategic_verdict == Verdict.DENY:
            return IntegratedJudgment(Verdict.DENY, chain)

        # 4. HumanFeedback gate
        hf_verdict = self._human_feedback_gate.decide(intent, capability)
        chain.append(GateResult(GateName.HUMAN_FEEDBACK, hf_verdict, f"HumanFeedback: {hf_verdict.value}"))

        # Combine: one DENY = DENY, DEFER beats ALLOW
        final = _combine_verdicts([r.verdict for r in chain])
        return IntegratedJudgment(final, chain)


# Default PowerZero implementation - vetoes nothing (open by default)
class DefaultPowerZero:
    """Default PowerZero that vetoes nothing."""

    def veto(self, intent: Intent) -> bool:
        return False


# Convenience function to create default pipeline
def create_default_pipeline(
    risk_gate: RiskGate,
    strategic_gate: StrategicGate,
    human_feedback_gate: HumanFeedbackGate,
) -> PrecedencePipeline:
    """Create a pipeline with default PowerZero (vetoes nothing)."""
    return PrecedencePipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=risk_gate,
        strategic_gate=strategic_gate,
        human_feedback_gate=human_feedback_gate,
    )