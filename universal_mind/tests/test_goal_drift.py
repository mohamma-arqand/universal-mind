"""Tests for goal-drift detection — notice when the path left the goal."""

from __future__ import annotations

from universal_mind.arete.goal_drift import assess_goal_drift


def test_on_course_is_not_drift() -> None:
    result = assess_goal_drift("summarize the quarterly report", "here is the quarterly report summary")
    assert result.drift is False
    assert result.overlap > 0.0


def test_wrong_outcome_is_drift() -> None:
    result = assess_goal_drift("summarize the quarterly report", "here is a recipe for chocolate cake")
    assert result.drift is True
    assert "drifted" in result.reason


def test_empty_outcome_is_drift() -> None:
    result = assess_goal_drift("summarize the report", "")
    assert result.drift is True


def test_empty_goal_is_drift_not_on_course() -> None:
    """An empty goal cannot be judged 'on course' — symmetric with empty outcome."""
    result = assess_goal_drift("", "anything")
    assert result.drift is True
    assert "no substantive tokens" in result.reason


def test_threshold_is_configurable() -> None:
    # A very low threshold lets a weak match count as on-course; a high one flags it.
    goal = "write a poem about the sea"
    outcome = "the sea is vast"
    assert assess_goal_drift(goal, outcome, threshold=0.0).drift is False
    assert assess_goal_drift(goal, outcome, threshold=0.9).drift is True


def test_assessment_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    a = assess_goal_drift("x y z", "x y z")
    try:
        a.drift = True  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True