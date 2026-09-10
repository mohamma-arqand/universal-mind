"""Tests for the chained judgment — the synthesis result itself is arbitrated."""

from __future__ import annotations

from universal_mind.memory.store import InMemoryStore
from universal_mind.synthesis import (
    FactSpecialist,
    SynthesisEngine,
    WriterSpecialist,
)


def _engine() -> SynthesisEngine:
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    return en


def test_successful_synthesis_is_verified() -> None:
    report = _engine().run("summarize knowledge then write the result")
    assert report.ok
    assert report.verified is True
    assert report.verification_reason


def test_failed_sub_execution_is_not_verified() -> None:
    """A broken specialist -> the synthesized D is refused verification."""
    from universal_mind.core.errors import CallerFault
    from universal_mind.core.intent import Determinism
    from universal_mind.io import ToolContract

    class BrokenSpecialist:
        contract = ToolContract(
            name="broken-gen", version="1.0.0", purpose="fails",
            signature="broken(intent, params)", cost_model="flat",
            latency_profile="instant", reliability="low", reversible=True,
            side_effects="none", required_secrets=[], determinism=Determinism.STRICT,
            domains=("general",), credibility=0.1,
        )

        def run(self, intent: object, params: dict[str, object]) -> bool:
            raise CallerFault("nope")

    en = SynthesisEngine(InMemoryStore())
    en.register("broken-gen", BrokenSpecialist())
    report = en.run("organize the general task")
    assert report.verified is False
    assert "failed" in report.verification_reason


def test_no_sub_execution_is_not_verified() -> None:
    from universal_mind.synthesis import SynthesisEngine

    # Direct: an empty execution list cannot be verified.
    ok, reason = SynthesisEngine._verify_synthesis("goal", [])
    assert ok is False
    assert reason == "no sub-executions to verify"


def test_verification_is_deterministic() -> None:
    a = _engine().run("summarize knowledge then write it")
    b = _engine().run("summarize knowledge then write it")
    assert a.verified == b.verified
    assert a.verification_reason == b.verification_reason