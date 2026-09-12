"""Prove the layering gate is LIVE in the real pipeline with the correct model.

The canonical model: higher layers command lower layers, never the reverse.
MOUTH(6) → ARETE(4) is legal; ARETE(4) → MOUTH(6) is an upward call and must be
refused. This asserts that direction through the actual PrecedencePipeline the
ExecutiveMind uses, so the law is enforced — not just documented.
"""

from __future__ import annotations

from typing import Any

from universal_mind.core.intent import Determinism, Intent
from universal_mind.gates.base import Gate, Verdict
from universal_mind.gates.power_zero import DefaultPowerZero
from universal_mind.gates.precedence import PrecedencePipeline, create_default_pipeline
from universal_mind.pantheon.registry import CapabilityDossier


class _Allow(Gate):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def precedence(self) -> int:
        return 0

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        return Verdict.ALLOW


def _intent(owner: str) -> Intent:
    return Intent(raw_text="x", goal="do a task", success_criteria=["y"], constraints=[],
                  deadline=None, determinism=Determinism.STRICT, owner_id=owner)


def _cap(name: str) -> CapabilityDossier:
    return CapabilityDossier(
        name=name, version="1", signature="x", purpose="x", cost_model="f",
        latency_profile="f", reliability="high", side_effects="none", reversible=True,
        required_secrets=[], failure_modes="none", dependencies=[],
        determinism=Determinism.STRICT, provenance={"explicit_fields": ["idempotent"]},
        idempotent=True,
    )


def _pipeline() -> PrecedencePipeline:
    return create_default_pipeline(
        power_zero=DefaultPowerZero(),
        risk_gate=_Allow("Risk"),
        strategic_gate=_Allow("Policy"),
        human_feedback_gate=_Allow("HumanFeedback"),
    )


def test_pipeline_denies_upward_and_allows_downward() -> None:
    pipeline = _pipeline()

    upward = pipeline.evaluate({"intent": _intent("arete"), "capability": _cap("mouth.commit")})
    assert upward.decision == Verdict.DENY

    downward = pipeline.evaluate({"intent": _intent("mouth"), "capability": _cap("arete.standard")})
    assert downward.decision == Verdict.ALLOW