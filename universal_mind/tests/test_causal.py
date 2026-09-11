"""Tests for causal reasoning — necessary vs incidental causes."""

from __future__ import annotations

from universal_mind.demiurge.causal import CausalFinding, TraceEvent, infer_causes


def _e(event_id: str, cause: str, effect: bool) -> TraceEvent:
    return TraceEvent(event_id=event_id, cause=cause, effect=effect)


def test_necessary_cause_is_detected() -> None:
    # Cause "A": effect always with A, never without A -> necessary.
    events = [
        _e("1", "A", True),
        _e("2", "A", True),
        _e("3", "B", False),
        _e("4", "B", False),
    ]
    findings = infer_causes(events)
    by_cause = {f.cause: f for f in findings}
    assert by_cause["A"].necessary is True
    assert by_cause["B"].necessary is False


def test_incidental_cause_is_distinguished() -> None:
    # "C" co-occurs with the effect but the effect also happens without it.
    events = [
        _e("1", "C", True),
        _e("2", "D", True),
        _e("3", "D", True),
    ]
    findings = infer_causes(events)
    by_cause = {f.cause: f for f in findings}
    assert by_cause["C"].necessary is False
    assert "incidental" in by_cause["C"].explanation


def test_empty_trace_has_no_findings() -> None:
    assert infer_causes([]) == ()


def test_support_and_absence_ratios_are_reported() -> None:
    events = [_e("1", "A", True), _e("2", "A", False)]
    findings = infer_causes(events)
    by_cause = {f.cause: f for f in findings}
    a = by_cause["A"]
    assert a.support_ratio == 0.5


def test_finding_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    f = CausalFinding("x", True, 1.0, 0.0, "expl")
    try:
        f.necessary = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True