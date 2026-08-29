"""
Tests for PowerZero precedence gate.
"""

import pytest
from dataclasses import dataclass
from universal_mind.gates.precedence import (
    PowerZero,
    RiskGate,
    StrategicGate,
    HumanFeedbackGate,
    PrecedencePipeline,
    Verdict,
    GateName,
    IntegratedJudgment,
    GateResult,
    DefaultPowerZero,
    create_default_pipeline,
    get_gate_order,
)
from universal_mind.core.intent import Intent
from universal_mind.pantheon.registry import CapabilityDossier


# ===== Test Fixtures =====

@dataclass
class MockIntent:
    goal: str = "test goal"
    params: dict = None
    success_criteria: str = "test criteria"
    owner_id: str = "test_owner"

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class MockCapabilityDossier:
    name: str = "test_capability"
    version: str = "1.0.0"
    idempotent: bool = True
    description: str = "test"


class AlwaysVetoPowerZero:
    """PowerZero that always vetoes."""
    def veto(self, intent: Intent) -> bool:
        return True


class NeverVetoPowerZero:
    """PowerZero that never vetoes."""
    def veto(self, intent: Intent) -> bool:
        return False


class ConditionalVetoPowerZero:
    """PowerZero that vetoes based on intent goal."""
    def __init__(self, veto_goals: list[str]):
        self.veto_goals = veto_goals

    def veto(self, intent: Intent) -> bool:
        return intent.goal in self.veto_goals


class AllowRiskGate:
    def assess(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.ALLOW


class DenyRiskGate:
    def assess(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.DENY


class DeferRiskGate:
    def assess(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.DEFER


class AllowStrategicGate:
    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.ALLOW


class DenyStrategicGate:
    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.DENY


class DeferStrategicGate:
    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.DEFER


class AllowHumanFeedbackGate:
    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.ALLOW


class DenyHumanFeedbackGate:
    def decide(self, intent: Intent, capability: CapabilityDossier) -> Verdict:
        return Verdict.DENY


# ===== Tests =====

def test_power_zero_absolute_veto():
    """Test that PowerZero veto stops all other gates."""
    pipeline = PrecedencePipeline(
        power_zero=AlwaysVetoPowerZero(),
        risk_gate=AllowRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert judgment.decision == Verdict.DENY
    assert len(judgment.chain) == 1
    assert judgment.chain[0].gate == GateName.POWER_ZERO
    assert judgment.chain[0].verdict == Verdict.DENY
    assert "PowerZero veto" in judgment.chain[0].reason


def test_power_zero_veto_allows_other_gates_to_run_when_false():
    """Test that when PowerZero doesn't veto, other gates execute."""
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=AllowRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert judgment.decision == Verdict.ALLOW
    assert len(judgment.chain) == 4  # All 4 gates ran
    assert judgment.chain[0].gate == GateName.POWER_ZERO
    assert judgment.chain[1].gate == GateName.RISK
    assert judgment.chain[2].gate == GateName.STRATEGIC
    assert judgment.chain[3].gate == GateName.HUMAN_FEEDBACK


def test_defer_beats_allow():
    """Test that DEFER beats ALLOW in final decision."""
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=DeferRiskGate(),  # DEFER
        strategic_gate=AllowStrategicGate(),  # ALLOW
        human_feedback_gate=AllowHumanFeedbackGate(),  # ALLOW
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    # DEFER beats ALLOW -> final should be DEFER
    assert judgment.decision == Verdict.DEFER


def test_one_deny_is_enough():
    """Test that one DENY anywhere = final DENY (fail-closed)."""
    # DENY at Risk
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=DenyRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert judgment.decision == Verdict.DENY
    # Should stop at Risk gate
    assert len(judgment.chain) == 2  # PowerZero + Risk
    assert judgment.chain[1].gate == GateName.RISK


def test_deny_at_strategic_stops_pipeline():
    """Test that DENY at Strategic stops before HumanFeedback."""
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=AllowRiskGate(),
        strategic_gate=DenyStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert judgment.decision == Verdict.DENY
    # Should stop at Strategic gate
    assert len(judgment.chain) == 3  # PowerZero + Risk + Strategic
    assert judgment.chain[2].gate == GateName.STRATEGIC


def test_deny_at_human_feedback():
    """Test DENY at HumanFeedback (last gate)."""
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=AllowRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=DenyHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert judgment.decision == Verdict.DENY
    assert len(judgment.chain) == 4  # All gates ran
    assert judgment.chain[3].gate == GateName.HUMAN_FEEDBACK


def test_gate_order_is_immutable():
    """Test that gate order cannot be changed from outside."""
    order = get_gate_order()

    # Order should be a tuple (immutable)
    assert isinstance(order, tuple)

    # Correct order
    assert order == (
        GateName.POWER_ZERO,
        GateName.RISK,
        GateName.STRATEGIC,
        GateName.HUMAN_FEEDBACK,
    )

    # Cannot modify
    with pytest.raises(AttributeError):
        order.append(GateName.POWER_ZERO)  # type: ignore

    # Original unchanged
    assert get_gate_order() == (
        GateName.POWER_ZERO,
        GateName.RISK,
        GateName.STRATEGIC,
        GateName.HUMAN_FEEDBACK,
    )


def test_conditional_veto():
    """Test PowerZero that conditionally vetoes based on intent."""
    pipeline = PrecedencePipeline(
        power_zero=ConditionalVetoPowerZero(veto_goals=["dangerous", "forbidden"]),
        risk_gate=AllowRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    capability = MockCapabilityDossier()

    # Should veto
    intent = MockIntent(goal="dangerous")
    judgment = pipeline.evaluate(intent, capability)
    assert judgment.decision == Verdict.DENY
    assert len(judgment.chain) == 1

    # Should NOT veto
    intent = MockIntent(goal="safe")
    judgment = pipeline.evaluate(intent, capability)
    assert judgment.decision == Verdict.ALLOW
    assert len(judgment.chain) == 4


def test_chain_records_all_gate_results():
    """Test that chain records every gate's verdict and reason."""
    pipeline = PrecedencePipeline(
        power_zero=NeverVetoPowerZero(),
        risk_gate=AllowRiskGate(),
        strategic_gate=DeferStrategicGate(),  # DEFER
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate(intent, capability)

    assert len(judgment.chain) == 4
    for i, result in enumerate(judgment.chain):
        assert isinstance(result, GateResult)
        assert result.gate == get_gate_order()[i]
        assert result.verdict in (Verdict.ALLOW, Verdict.DENY, Verdict.DEFER)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0


def test_integrated_judgment_allowed_property():
    """Test IntegratedJudgment.allowed property."""
    allowed = IntegratedJudgment(Verdict.ALLOW, [])
    assert allowed.allowed is True

    denied = IntegratedJudgment(Verdict.DENY, [])
    assert denied.allowed is False

    deferred = IntegratedJudgment(Verdict.DEFER, [])
    assert deferred.allowed is False


def test_create_default_pipeline():
    """Test create_default_pipeline convenience function."""
    pipeline = create_default_pipeline(
        risk_gate=AllowRiskGate(),
        strategic_gate=AllowStrategicGate(),
        human_feedback_gate=AllowHumanFeedbackGate(),
    )

    assert isinstance(pipeline, PrecedencePipeline)
    assert isinstance(pipeline._power_zero, DefaultPowerZero)

    # Default PowerZero should not veto
    assert pipeline._power_zero.veto(MockIntent()) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])