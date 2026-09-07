"""
Tests for unified gate pipeline (PrecedencePipeline + PowerZero + adapters).
"""

from dataclasses import dataclass
from typing import Any

import pytest

from universal_mind.gates import (
    AlwaysVetoPowerZero,
    ConditionalVetoPowerZero,
    DefaultPowerZero,
    Gate,
    GateResult,
    PipelineJudgment,
    PrecedencePipeline,
    Verdict,
    combine_verdicts,
    create_default_pipeline,
)

# ===== Test Fixtures =====


@dataclass
class MockIntent:
    goal: str = "test goal"
    params: dict[str, Any] | None = None
    success_criteria: str = "test criteria"
    owner_id: str = "test_owner"

    def __post_init__(self) -> None:
        if self.params is None:
            self.params = {}


@dataclass
class MockCapabilityDossier:
    name: str = "test_capability"
    version: str = "1.0.0"
    idempotent: bool = True
    description: str = "test"


# Simple gate implementations for testing
class TestGate(Gate):
    """Simple test gate that returns a fixed verdict."""

    # Not a test class - a shared stub. Prevents pytest collecting it (and its
    # Test* subclasses) as test classes.
    __test__ = False

    def __init__(self, name: str, verdict: Verdict) -> None:
        # Name must be one of the GATE_PRECEDENCE entries
        valid_names = ["PowerZero", "Layering", "Policy", "Risk", "HumanFeedback"]
        if name not in valid_names:
            raise ValueError(f"Invalid gate name '{name}'. Must be one of: {valid_names}")
        self._name = name
        self._verdict = verdict

    @property
    def name(self) -> str:
        return self._name

    @property
    def precedence(self) -> int:
        # Stub gate: precedence is not used by PrecedencePipeline (order comes
        # from GATE_PRECEDENCE by name), but Gate requires it declaratively.
        return 0

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        return self._verdict


class TestPolicyGate(TestGate):
    """Test gate with Policy name."""
    def __init__(self, verdict: Verdict) -> None:
        super().__init__("Policy", verdict)


class TestRiskGate(TestGate):
    """Test gate with Risk name."""
    def __init__(self, verdict: Verdict) -> None:
        super().__init__("Risk", verdict)


class TestHumanFeedbackGate(TestGate):
    """Test gate with HumanFeedback name."""
    def __init__(self, verdict: Verdict) -> None:
        super().__init__("HumanFeedback", verdict)


class TestLayeringGate(TestGate):
    """Test gate with Layering name."""
    def __init__(self, verdict: Verdict) -> None:
        super().__init__("Layering", verdict)


class TestPowerZeroGate(TestGate):
    """Test gate with PowerZero name."""
    def __init__(self, verdict: Verdict) -> None:
        super().__init__("PowerZero", verdict)


# ===== Tests =====

def test_pipeline_deterministic_ordering() -> None:
    """Test that pipeline sorts gates by GATE_PRECEDENCE order."""
    gates: list[Gate] = [
        TestPolicyGate(Verdict.ALLOW),    # Policy (800) - index 2
        TestLayeringGate(Verdict.ALLOW),  # Layering (900) - index 1
        TestRiskGate(Verdict.ALLOW),      # Risk (600) - index 3
    ]
    pipeline = PrecedencePipeline(gates)

    # Should be ordered by GATE_PRECEDENCE: Layering (1), Policy (2), Risk (3)
    assert [g.name for g in pipeline.gates] == ["Layering", "Policy", "Risk"]


def test_pipeline_short_circuit_on_deny() -> None:
    """Test that DENY short-circuits the pipeline."""
    gates: list[Gate] = [
        TestPolicyGate(Verdict.ALLOW),       # Policy - index 2
        TestRiskGate(Verdict.DENY),          # Risk - index 3 - This should stop execution
        TestHumanFeedbackGate(Verdict.ALLOW),  # HumanFeedback - index 4 - Should be skipped
    ]
    pipeline = PrecedencePipeline(gates)

    judgment = pipeline.evaluate({"intent": MockIntent()})

    assert judgment.decision == Verdict.DENY
    assert len(judgment.trace) == 3  # All gates in trace (including skipped)
    assert judgment.trace[0].gate_name == "Policy"
    assert judgment.trace[0].verdict == Verdict.ALLOW
    assert judgment.trace[0].skipped is False
    assert judgment.trace[1].gate_name == "Risk"
    assert judgment.trace[1].verdict == Verdict.DENY
    assert judgment.trace[1].skipped is False
    assert judgment.trace[2].gate_name == "HumanFeedback"
    assert judgment.trace[2].skipped is True
    assert judgment.trace[2].skip_reason and "hard veto" in judgment.trace[2].skip_reason


def test_pipeline_no_deny_runs_all() -> None:
    """Test that without DENY, all gates run and verdicts combine."""
    gates: list[Gate] = [
        TestPolicyGate(Verdict.ALLOW),
        TestRiskGate(Verdict.DEFER),
        TestHumanFeedbackGate(Verdict.ALLOW),
    ]
    pipeline = PrecedencePipeline(gates)

    judgment = pipeline.evaluate({"intent": MockIntent()})

    assert judgment.decision == Verdict.DEFER  # DEFER beats ALLOW
    assert len(judgment.trace) == 3
    for t in judgment.trace:
        assert t.skipped is False


def test_pipeline_allow_only() -> None:
    """Test all ALLOW gives ALLOW."""
    gates: list[Gate] = [
        TestPolicyGate(Verdict.ALLOW),
        TestRiskGate(Verdict.ALLOW),
    ]
    pipeline = PrecedencePipeline(gates)

    judgment = pipeline.evaluate({"intent": MockIntent()})

    assert judgment.decision == Verdict.ALLOW
    assert judgment.allowed is True


def test_power_zero_absolute_veto() -> None:
    """Test that PowerZero veto stops all other gates."""
    pipeline = create_default_pipeline(
        power_zero=AlwaysVetoPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert judgment.decision == Verdict.DENY
    # All 5 gates in trace: PowerZero evaluated, others skipped (Layering added by default)
    assert len(judgment.trace) == 5
    assert judgment.trace[0].gate_name == "PowerZero"
    assert judgment.trace[0].verdict == Verdict.DENY
    assert judgment.trace[0].skipped is False
    for i in range(1, 5):
        assert judgment.trace[i].skipped is True
        assert judgment.trace[i].verdict == Verdict.DENY


def test_power_zero_pass_allows_other_gates() -> None:
    """Test that when PowerZero doesn't veto, other gates execute."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert judgment.decision == Verdict.ALLOW
    assert len(judgment.trace) == 5  # All 5 gates ran (PowerZero, Layering, Policy, Risk, HumanFeedback)
    assert judgment.trace[0].gate_name == "PowerZero"
    assert judgment.trace[1].gate_name == "Layering"  # Layering gate is always added
    assert judgment.trace[2].gate_name == "Policy"
    assert judgment.trace[3].gate_name == "Risk"
    assert judgment.trace[4].gate_name == "HumanFeedback"


def test_defer_beats_allow() -> None:
    """Test that DEFER beats ALLOW in final decision."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.DEFER),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    # DEFER beats ALLOW -> final should be DEFER
    assert judgment.decision == Verdict.DEFER


def test_one_deny_is_enough() -> None:
    """Test that one DENY anywhere = final DENY (fail-closed)."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.DENY),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert judgment.decision == Verdict.DENY
    assert len(judgment.trace) == 5
    assert judgment.trace[0].gate_name == "PowerZero"
    assert judgment.trace[0].verdict == Verdict.ALLOW
    assert judgment.trace[1].gate_name == "Layering"
    assert judgment.trace[1].verdict == Verdict.ALLOW
    assert judgment.trace[2].gate_name == "Policy"
    assert judgment.trace[2].verdict == Verdict.ALLOW
    assert judgment.trace[3].gate_name == "Risk"
    assert judgment.trace[3].verdict == Verdict.DENY
    for i in range(4, 5):
        assert judgment.trace[i].skipped is True
        assert judgment.trace[i].verdict == Verdict.DENY


def test_deny_at_strategic_stops_pipeline() -> None:
    """Test that DENY at Strategic stops before HumanFeedback."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.DENY),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert judgment.decision == Verdict.DENY
    assert len(judgment.trace) == 5
    assert judgment.trace[0].gate_name == "PowerZero"
    assert judgment.trace[0].verdict == Verdict.ALLOW
    assert judgment.trace[1].gate_name == "Layering"
    assert judgment.trace[1].verdict == Verdict.ALLOW
    assert judgment.trace[2].gate_name == "Policy"
    assert judgment.trace[2].verdict == Verdict.DENY
    assert judgment.trace[3].gate_name == "Risk"
    assert judgment.trace[3].skipped is True
    assert judgment.trace[3].verdict == Verdict.DENY
    assert judgment.trace[4].gate_name == "HumanFeedback"
    assert judgment.trace[4].skipped is True
    assert judgment.trace[4].verdict == Verdict.DENY


def test_deny_at_human_feedback() -> None:
    """Test DENY at HumanFeedback (last gate)."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.DENY),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert judgment.decision == Verdict.DENY
    assert len(judgment.trace) == 5  # All gates ran
    assert judgment.trace[4].gate_name == "HumanFeedback"


def test_conditional_veto() -> None:
    """Test PowerZero that conditionally vetoes based on intent."""
    pipeline = create_default_pipeline(
        power_zero=ConditionalVetoPowerZero(veto_goals=["dangerous", "forbidden"]),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    capability = MockCapabilityDossier()

    # Should veto
    intent = MockIntent(goal="dangerous")
    judgment = pipeline.evaluate({"intent": intent, "capability": capability})
    assert judgment.decision == Verdict.DENY
    assert len(judgment.trace) == 5
    assert judgment.trace[0].gate_name == "PowerZero"  # All PowerZero variants share the same gate type name
    assert judgment.trace[0].verdict == Verdict.DENY
    for i in range(1, 5):
        assert judgment.trace[i].skipped is True

    # Should NOT veto
    intent = MockIntent(goal="safe")
    judgment = pipeline.evaluate({"intent": intent, "capability": capability})
    assert judgment.decision == Verdict.ALLOW
    assert len(judgment.trace) == 5


def test_chain_records_all_gate_results() -> None:
    """Test that trace records every gate's verdict and reason."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.DEFER),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    intent = MockIntent(goal="test")
    capability = MockCapabilityDossier()

    judgment = pipeline.evaluate({"intent": intent, "capability": capability})

    assert len(judgment.trace) == 5
    for i, result in enumerate(judgment.trace):
        assert isinstance(result, GateResult)
        assert result.gate_name == pipeline.gates[i].name
        assert result.precedence == i  # Position in GATE_PRECEDENCE
        assert result.verdict in (Verdict.ALLOW, Verdict.DENY, Verdict.DEFER)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0


def test_pipeline_judgment_properties() -> None:
    """Test PipelineJudgment helper properties."""
    allowed = PipelineJudgment(Verdict.ALLOW, [])
    assert allowed.allowed is True
    assert allowed.deferred is False
    assert allowed.denied is False

    denied = PipelineJudgment(Verdict.DENY, [])
    assert denied.allowed is False
    assert denied.deferred is False
    assert denied.denied is True

    deferred = PipelineJudgment(Verdict.DEFER, [])
    assert deferred.allowed is False
    assert deferred.deferred is True
    assert deferred.denied is False


def test_combine_verdicts() -> None:
    """Test the combine_verdicts helper function."""
    assert combine_verdicts([Verdict.ALLOW, Verdict.ALLOW]) == Verdict.ALLOW
    assert combine_verdicts([Verdict.ALLOW, Verdict.DEFER]) == Verdict.DEFER
    assert combine_verdicts([Verdict.ALLOW, Verdict.DENY]) == Verdict.DENY
    assert combine_verdicts([Verdict.DEFER, Verdict.DENY]) == Verdict.DENY
    assert combine_verdicts([Verdict.DEFER, Verdict.DEFER]) == Verdict.DEFER


def test_create_default_pipeline() -> None:
    """Test create_default_pipeline convenience function."""
    pipeline = create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=TestRiskGate(Verdict.ALLOW),
        strategic_gate=TestPolicyGate(Verdict.ALLOW),
        human_feedback_gate=TestHumanFeedbackGate(Verdict.ALLOW),
    )

    assert isinstance(pipeline, PrecedencePipeline)
    assert isinstance(pipeline.gates[0], DefaultPowerZero)
    assert len(pipeline.gates) == 5  # PowerZero, Layering, Policy, Risk, HumanFeedback

    # Default PowerZero should not veto
    assert pipeline.gates[0].veto(MockIntent()) is False  # type: ignore[arg-type]


def test_duplicate_gate_names_raises() -> None:
    """Test that duplicate gate names raise ValueError."""
    gates: list[Gate] = [
        TestPolicyGate(Verdict.ALLOW),
        TestPolicyGate(Verdict.ALLOW),
    ]
    with pytest.raises(ValueError, match="Duplicate gate names"):
        PrecedencePipeline(gates)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])