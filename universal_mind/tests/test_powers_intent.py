"""Tests for the IntentTranslation power (raw text -> typed Intent)."""

from __future__ import annotations

import asyncio
from typing import Any

from universal_mind.powers.intent import (
    InMemoryIntentTranslation,
    IntentTranslationInput,
)


def _translate(raw: str) -> Any:
    inp = IntentTranslationInput(raw_text=raw, owner_id="owner")
    return asyncio.run(InMemoryIntentTranslation().translate(inp))


def test_simple_goal_extraction() -> None:
    out = _translate("Write a report. Must be done.")
    assert out.intent.goal == "Write a report"
    assert out.confidence > 0


def test_success_criteria_extraction() -> None:
    out = _translate("Build a thing. It must be fast and should be cheap.")
    assert "fast" in " ".join(out.intent.success_criteria) or "cheap" in " ".join(out.intent.success_criteria)
    assert out.extracted_fields.get("criteria")


def test_constraints_extraction() -> None:
    out = _translate("Write a report without errors and avoid jargon.")
    assert any("without" in c or "avoid" in c for c in out.intent.constraints)


def test_determinism_creative_detection() -> None:
    out = _translate("Brainstorm some creative ideas.")
    assert out.intent.determinism.value == "creative"


def test_determinism_defaults_strict() -> None:
    out = _translate("Write a report.")
    assert out.intent.determinism.value == "strict"


def test_empty_input_falls_back_to_default() -> None:
    out = _translate("")
    assert out.intent.goal  # non-empty fallback
    assert out.warnings


def test_confidence_bounds_are_0_1() -> None:
    out = _translate("Write a report. Must be done without errors.")
    assert 0.0 <= out.confidence <= 1.0


def test_query_protocol_shape() -> None:
    """The output matches the documented IntentTranslationOutput shape."""
    out = _translate("Write a report.")
    assert hasattr(out, "intent")
    assert hasattr(out, "confidence")
    assert hasattr(out, "extracted_fields")
    assert hasattr(out, "warnings")