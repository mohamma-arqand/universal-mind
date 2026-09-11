"""Tests for provable policy — every decision as a verifiable reason chain."""

from __future__ import annotations

from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
from universal_mind.arete.policy_trace import PolicyStep, PolicyTrace, trace_verdict
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output="out",
        metadata={"virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}},
    )


def test_allow_verdict_has_verifiable_steps() -> None:
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[_candidate("x", 0.9)]))
    trace = trace_verdict(verdict)
    assert trace.decision == "allow"
    assert trace.winner == "x"
    assert any(s.check == "winner" for s in trace.steps)
    assert any(s.check == "measurement" for s in trace.steps)
    assert trace.verifiable is True


def test_deny_verdict_records_no_winner_step() -> None:
    from universal_mind.powers.judgment import Verdict

    # A candidate below every virtue is below the accept threshold -> denied.
    c = CandidateOutput(strategy_id="weak", output="out", metadata={
        "virtues": {"justice": 0.1, "wisdom": 0.1, "courage": 0.1, "temperance": 0.1}})
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[c]))
    assert verdict.decision is Verdict.DENY
    trace = trace_verdict(verdict)
    assert trace.decision == Verdict.DENY.value
    assert trace.winner is None
    assert any(s.check == "no_winner" for s in trace.steps)


def test_disqualified_candidate_has_hard_gate_step() -> None:
    # Low justice -> disqualified -> a hard_gate step with passed=False.
    c = CandidateOutput(strategy_id="bad", output="out", metadata={
        "virtues": {"justice": 0.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}})
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[c]))
    trace = trace_verdict(verdict)
    assert any(s.check == "hard_gate" and s.passed is False for s in trace.steps)


def test_every_step_carries_a_value() -> None:
    verdict = InMemoryArbiter().arbitrate(Dispute(goal="pick", candidates=[_candidate("x", 0.9)]))
    trace = trace_verdict(verdict)
    assert all(s.value is not None for s in trace.steps)


def test_trace_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    t = PolicyTrace("allow", "x", (PolicyStep("s", "c", 1.0, True),), True)
    try:
        t.verifiable = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True