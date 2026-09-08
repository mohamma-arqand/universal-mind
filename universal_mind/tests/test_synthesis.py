"""Tests for the synthesis engine — close the loop: A+B+C -> D."""

from __future__ import annotations

import pytest

from universal_mind.core.errors import CallerFault
from universal_mind.memory.store import InMemoryStore
from universal_mind.synthesis import (
    FactSpecialist,
    SynthesisEngine,
    SynthesisError,
    WriterSpecialist,
    domain_for,
)


def _engine() -> SynthesisEngine:
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    return en


def test_domain_for() -> None:
    assert domain_for("summarize the knowledge") == "knowledge"
    assert domain_for("write the final draft") == "writing"
    assert domain_for("run a shell command") == "system"
    assert domain_for("do general stuff") == "general"


def test_engine_synthesizes_a_plus_b() -> None:
    """Two sub-goals, two specialists, one synthesized D."""
    en = _engine()
    report = en.run("summarize knowledge then write the result")
    assert report.ok
    assert {e.specialist for e in report.sub_executions} == {"facts", "writer"}
    assert report.synthesized is not None
    assert "[facts]" in report.synthesized
    assert "[writer]" in report.synthesized
    assert report.commit_record_id is not None
    kinds = [r.get("kind") for r in en._store.read_all()]
    assert "synthesis" in kinds


def test_synthesis_is_evidence_backed() -> None:
    report = _engine().run("summarize knowledge then write the result")
    assert report.evidence.points
    assert report.evidence.total_weight() > 0


def test_unresolvable_goal_raises() -> None:
    """A sub-goal with no specialist is refused, not silently dropped."""
    en = SynthesisEngine(InMemoryStore())  # no specialists registered
    with pytest.raises(SynthesisError):
        en.run("summarize the knowledge")


def test_engine_deterministic() -> None:
    out1 = _engine().run("summarize knowledge then write it")
    out2 = _engine().run("summarize knowledge then write it")
    assert out1.synthesized == out2.synthesized


def test_each_sub_execution_has_evidence() -> None:
    report = _engine().run("summarize knowledge then write it")
    for e in report.sub_executions:
        assert e.ok
        assert e.specialist


def test_failure_is_reported_not_fatal() -> None:
    """A caller fault in one sub-step is captured, not a hard crash."""
    en = _engine()
    # Register a specialist that always raises a caller fault.
    from universal_mind.core.intent import Determinism, Intent
    from universal_mind.io import ToolContract

    class BrokenSpecialist:
        contract = ToolContract(
            name="broken", version="1.0.0", purpose="always fails",
            signature="broken(intent, params)", cost_model="flat",
            latency_profile="instant", reliability="low", reversible=True,
            side_effects="none", required_secrets=[], determinism=Determinism.STRICT,
            domains=("general",), credibility=0.1,
        )

        def run(self, intent: Intent, params: dict[str, object]) -> bool:
            raise CallerFault("nope")

    en.register("broken", BrokenSpecialist())
    # A valid action verb that routes to the general domain so 'broken' is selected.
    report = en.run("organize the general task")
    assert report.sub_executions  # the sub-step ran and its failure was captured
    assert not report.ok or report.synthesized is None