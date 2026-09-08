"""Tests for MOUTH — raw speech becomes an evidenced, typed commitment."""

from __future__ import annotations

import pytest

from universal_mind.arete.evidence import EvidenceBundle, EvidenceSource
from universal_mind.core.intent import Determinism
from universal_mind.mouth import (
    InMemoryMouth,
    IntentConflict,
    IntentNeedsClarification,
    Mouth,
    StructuredIntent,
)


def test_empty_speech_needs_clarification() -> None:
    """Empty input is refused, never committed silently."""
    with pytest.raises(IntentNeedsClarification):
        InMemoryMouth().commit("", "owner")


def test_vague_goal_needs_clarification() -> None:
    """Bare/too-short goal is refused with a clarifying question."""
    with pytest.raises(IntentNeedsClarification) as exc:
        InMemoryMouth().commit("do it", "owner")
    assert exc.value.questions


def test_clear_request_commits_with_goal() -> None:
    """A clear request yields a StructuredIntent whose goal is anchored."""
    text = "Summarize the quarterly report. Must be under 200 words."
    structured = InMemoryMouth().commit(text, "owner")
    assert isinstance(structured, StructuredIntent)
    assert structured.intent.goal
    assert structured.intent.success_criteria
    assert structured.intent.owner_id == "owner"


def test_every_committed_field_has_evidence() -> None:
    """Goal and criteria are evidence-anchored, not asserted."""
    structured = InMemoryMouth().commit(
        "Write a report. So that the board can decide.",
        "owner",
    )
    assert "goal" in structured.field_evidence
    assert isinstance(structured.field_evidence["goal"], EvidenceBundle)
    assert structured.field_evidence["goal"].points
    # The evidence source is HUMAN (comes from the user's own words).
    assert structured.field_evidence["goal"].points[0].source is EvidenceSource.HUMAN


def test_determinism_inferred_from_keywords() -> None:
    """Creative markers switch the intent to CREATIVE determinism."""
    creative = InMemoryMouth().commit(
        "Brainstorm three campaign ideas. Must be creative.",
        "owner",
    )
    assert creative.intent.determinism is Determinism.CREATIVE
    strict = InMemoryMouth().commit("Compute the sum. Must be exact.", "owner")
    assert strict.intent.determinism is Determinism.STRICT


def test_contradiction_raises_conflict() -> None:
    """A self-contradicting request is refused as a conflict, not silently kept."""
    with pytest.raises(IntentConflict):
        InMemoryMouth().commit(
            "Do not proceed, but proceed immediately.",
            "owner",
        )


def test_mouth_is_deterministic() -> None:
    """Identical input yields an identical commitment."""
    text = "Summarize the report. Should be concise."
    first = InMemoryMouth().commit(text, "o")
    second = InMemoryMouth().commit(text, "o")
    assert first == second
    assert first.intent == second.intent


def test_extractor_injection() -> None:
    """A custom extractor can drive parsing while the contract stays identical."""
    mouth = InMemoryMouth(extractor=lambda t: ("summarize custom goal", ["done"], [], Determinism.STRICT))
    structured = mouth.commit("anything with some words here", "owner")
    assert structured.intent.goal == "summarize custom goal"
    assert structured.intent.success_criteria == ["done"]


def test_mouth_protocol_conformance() -> None:
    """InMemoryMouth conforms to the Mouth protocol at runtime."""
    mouth: Mouth = InMemoryMouth()
    assert isinstance(mouth, Mouth)


def test_structured_intent_payload() -> None:
    """to_payload serializes intent + per-field evidence citations."""
    structured = InMemoryMouth().commit("Summarize it. Need it short.", "o")
    payload = structured.to_payload()
    assert "intent" in payload
    assert "field_evidence" in payload
    assert payload["field_evidence"]["goal"]  # non-empty citations