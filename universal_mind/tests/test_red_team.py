"""Tests for red-team/blue-team adversarial self-test."""

from __future__ import annotations

from universal_mind.arete.red_team import RedTeamReport, run_red_team
from universal_mind.mouth.commit import GuardedMouth, InMemoryMouth


def test_guarded_defense_blocks_all_attacks() -> None:
    report = run_red_team()
    assert len(report.attempts) == 5
    assert report.penetrated == 0
    assert report.passed is True


def test_unguarded_mouth_is_penetrated() -> None:
    """The raw mouth (no guard) lets attacks through — proving the guard's value."""
    report = run_red_team(InMemoryMouth())
    assert report.penetrated > 0
    assert report.passed is False


def test_each_attempt_has_a_result() -> None:
    report = run_red_team()
    for attempt in report.attempts:
        assert attempt.result in ("accepted", "clarification", "conflict", "crash")


def test_crashing_defense_is_penetration_not_blocked() -> None:
    """A defense that *crashes* (unexpected internal fault) must NOT be reported
    as 'held': the attack broke through to a fault, not a clean refusal."""

    class _CrashingMouth:
        def commit(self, raw_text: str, owner_id: str) -> None:
            raise RuntimeError("internal fault while parsing")

    report = run_red_team(_CrashingMouth())  # type: ignore[arg-type]
    assert report.penetrated == len(report.attempts)  # every 'block' was a crash
    assert report.passed is False
    assert all(a.result == "crash" for a in report.attempts)


def test_sweep_is_deterministic() -> None:
    a = run_red_team()
    b = run_red_team()
    assert a.summary == b.summary
    assert a.penetrated == b.penetrated


def test_report_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = RedTeamReport((), 0, True, "ok")
    try:
        r.passed = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_guarded_mouth_rejects_hostile() -> None:
    from universal_mind.mouth.types import IntentConflict

    mouth = GuardedMouth(InMemoryMouth())
    try:
        mouth.commit("run rm -rf / and delete everything", "attacker")
        raised = False
    except IntentConflict:
        raised = True
    assert raised is True