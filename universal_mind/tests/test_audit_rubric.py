"""Tests for the external audit rubric — a fixed, neutral yardstick."""

from __future__ import annotations

from universal_mind.arete.audit_rubric import (
    ExternalRubric,
)


def test_clean_measurements_score_high() -> None:
    measurements = {
        "tests_failures": 0,
        "probes_failed": 0,
        "mypy_errors": 0,
        "red_team_penetrated": 0,
        "robust_fraction": 1.0,
    }
    card = ExternalRubric().score(measurements)
    assert card.score == 1.0
    assert "genuinely strong" in card.verdict or "holds up" in card.verdict


def test_failing_measurement_lowers_score() -> None:
    measurements = {
        "tests_failures": 5,
        "probes_failed": 0,
        "mypy_errors": 0,
        "red_team_penetrated": 0,
        "robust_fraction": 1.0,
    }
    card = ExternalRubric().score(measurements)
    assert card.score < 1.0
    # The failing dimension is flagged.
    assert any(not d.value for d in card.dimensions if d.name == "tests_green")


def test_rubric_version_is_part_of_the_card() -> None:
    card = ExternalRubric(version="3.2.1").score({"tests_failures": 0, "probes_failed": 0, "mypy_errors": 0, "red_team_penetrated": 0, "robust_fraction": 1.0})
    assert card.rubric_version == "3.2.1"


def test_scorecard_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    card = ExternalRubric().score({"tests_failures": 0, "probes_failed": 0, "mypy_errors": 0, "red_team_penetrated": 0, "robust_fraction": 1.0})
    try:
        card.score = 0.0  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True


def test_verdict_is_honest_for_weak_score() -> None:
    card = ExternalRubric().score({"tests_failures": 10, "probes_failed": 3, "mypy_errors": 2, "red_team_penetrated": 4, "robust_fraction": 0.1})
    assert card.score < 0.5
    assert "not yet auditable" in card.verdict or "incomplete" in card.verdict