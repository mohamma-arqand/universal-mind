"""Tests for significance-biased forgetting (least-valuable trims first)."""

from __future__ import annotations

from universal_mind.memory.lifespan import _significance


def test_standard_is_most_significant() -> None:
    assert _significance({"kind": "standard"}) == 90
    assert _significance({"kind": "human_consent"}) == 90


def test_verified_synthesis_outranks_unverified() -> None:
    assert _significance({"kind": "synthesis", "payload": {"verified": True}}) == 70
    assert _significance({"kind": "synthesis", "payload": {}}) == 40


def test_generated_power_and_feedback_ranked() -> None:
    assert _significance({"kind": "generated_power"}) == 60
    assert _significance({"kind": "feedback"}) == 50


def test_unknown_kind_is_least_significant() -> None:
    assert _significance({"kind": "random-noise"}) == 10


def test_significance_is_deterministic() -> None:
    r = {"kind": "synthesis", "payload": {"verified": True}}
    assert _significance(r) == _significance(r)