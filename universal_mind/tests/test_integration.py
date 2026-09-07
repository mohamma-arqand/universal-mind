"""Tests for the integration face — ExecutiveMind + Gateway + ARETĒ + Prometheus."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from universal_mind.core.errors import TaskFailure
from universal_mind.core.intent import Determinism, Intent
from universal_mind.integration import (
    GatewayCapability,
    InMemoryIntegrationHarness,
    IntegrationError,
    UniversalMindRuntime,
)
from universal_mind.io.errors import ProviderError, ProviderPermanent
from universal_mind.io.gateway import EchoProvider, Gateway, Message, ScriptedProvider
from universal_mind.pantheon.contracts import ContractViolation

# Matches ScriptedProvider's script element type (public view for the harness).
_OutcomeArg = ProviderError | str | Callable[[list[Message]], object]


def _harness(script: list[_OutcomeArg], name: str = "scripted") -> InMemoryIntegrationHarness:
    provider = ScriptedProvider(script, name=name)
    return InMemoryIntegrationHarness(Gateway([provider]))


def _intent(goal: str = "summarize", raw: str = "Please summarize this document") -> Intent:
    return Intent.from_raw(
        goal=goal, raw_text=raw, success_criteria=["done"],
        owner_id="sovereign", determinism=Determinism.CREATIVE,
    )


def test_gateway_capability_serves_content() -> None:
    """GatewayCapability returns the provider content as a CapabilityResult."""
    capability = GatewayCapability(Gateway([EchoProvider()]))
    result = capability.execute(_intent(raw="hello world"), {"owner_id": "sovereign"})
    assert result.ok
    assert result.output["content"] == "hello world"
    assert result.output["provider"] == "echo"


def test_gateway_capability_failure_raises_task_failure() -> None:
    """A dead provider chain surfaces as a retryable TaskFailure."""
    capability = GatewayCapability(Gateway([ScriptedProvider([ProviderPermanent("down")])]))
    with pytest.raises(TaskFailure):
        capability.execute(_intent(), {})


def test_gateway_capability_validate_intent() -> None:
    """An empty prompt is a caller fault, not a system fault."""
    capability = GatewayCapability(Gateway([EchoProvider()]))
    blank = Intent(
        raw_text="",
        goal="",
        success_criteria=["x"],
        constraints=[],
        deadline=None,
        determinism=Determinism.CREATIVE,
        owner_id="sovereign",
    )
    with pytest.raises(ContractViolation):
        capability.validate_intent(blank)


def test_full_integration_run() -> None:
    """The composed loop executes and the gateway output wins arbitration."""
    harness = _harness(["An excellent, fair, verified answer."])
    report = harness.run("summarize", "Please summarize this document")
    assert report.execution_status == "ok"
    assert report.ok is True
    assert report.result_content is not None
    assert report.result_provider == "scripted"
    assert report.arbitration.winner_strategy_id == "gateway"
    assert report.arbitration.decision.value == "allow"


def test_arbitration_prefers_gateway_over_baseline() -> None:
    """The gateway candidate scores above the plain baseline echo."""
    harness = _harness(["Just answer"])
    report = harness.run("summarize", "bare note")
    scores = {s.candidate_strategy_id: s.excellence for s in report.arbitration.scorecards}
    assert scores["gateway"] > scores["baseline"]


def test_ledger_audits_the_run() -> None:
    """The shared ledger contains the full ExecutiveMind audit trail."""
    harness = _harness(["ok"])
    harness.run("summarize", "Please summarize this document")
    kinds = [r.get("kind") for r in harness.store.read_all()]
    assert "capability_registration" in kinds
    assert "intent_received" in kinds
    assert "risk_assessment" in kinds
    assert "capability_selected" in kinds
    assert "capability_result" in kinds


def test_protocol_conformance() -> None:
    """The harness conforms to the UniversalMindRuntime protocol."""
    runtime: UniversalMindRuntime = _harness(["x"])
    assert isinstance(runtime, UniversalMindRuntime)


def test_deterministic_across_instances() -> None:
    """Identical inputs and providers produce an identical composed outcome."""
    def once() -> tuple[str, str | None]:
        report = _harness(["Deterministic result"]).run("summarize", "same input")
        return report.execution_status, report.arbitration.winner_strategy_id

    assert once() == once()


def test_failing_provider_raises_integration_error_and_audits_fault() -> None:
    """A dead provider surfaces IntegrationError and leaves a fault record."""
    harness = _harness([ProviderPermanent("out of service")])
    with pytest.raises(IntegrationError):
        harness.run("summarize", "Please summarize this document")
    kinds = [r.get("kind") for r in harness.store.read_all()]
    assert "fault" in kinds


def test_prometheus_observes_same_ledger() -> None:
    """Prometheus reads the composed run's ledger without error."""
    harness = _harness(["ok"])
    report = harness.run("summarize", "summarize this")
    assert isinstance(report.evolution_summary, str) and report.evolution_summary
    assert isinstance(report.proposals, tuple)