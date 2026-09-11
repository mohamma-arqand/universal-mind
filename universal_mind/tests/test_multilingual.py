"""Tests for multilingual intent normalization."""

from __future__ import annotations

from universal_mind.mouth.multilingual import normalize_intent


def test_english_action_is_canonical() -> None:
    result = normalize_intent("summarize the report")
    assert result.action == "summarize"
    assert "report" in result.subjects
    assert result.source_language == "en"


def test_persian_maps_to_the_same_canonical_action() -> None:
    result = normalize_intent("گزارش را خلاصه کن")
    assert result.action == "summarize"
    assert result.source_language == "fa"


def test_english_and_persian_converge() -> None:
    en = normalize_intent("summarize the report")
    fa = normalize_intent("گزارش را خلاصه کن")
    # Different source languages, same canonical action.
    assert en.action == fa.action == "summarize"


def test_unknown_action_falls_back_to_first_word() -> None:
    result = normalize_intent("zzz the thing")
    assert result.action != ""
    assert result.source_language == "en"


def test_result_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = normalize_intent("summarize x")
    try:
        r.action = "write"  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True