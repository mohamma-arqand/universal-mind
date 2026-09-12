"""Tests for semantic synthesis (super-platform Phase 3c)."""

from __future__ import annotations

from universal_mind.semantic_synthesis import weave_semantic


def test_weave_folds_fact_into_draft() -> None:
    result = weave_semantic([
        ("facts", {"fact": "the measured value is 42 units"}),
        ("writer", {"draft": "Final: the telemetry report."}),
    ])
    assert result.method == "semantic"
    # One indivisible utterance, not two stacked strings.
    assert "the measured value is 42 units" in result.artifact
    assert "Final: the telemetry report" in result.artifact


def test_weave_appends_decision_as_note() -> None:
    result = weave_semantic([
        ("writer", {"draft": "Final: the plan."}),
        ("judge", {"decision": "allow"}),
    ])
    assert result.method == "semantic"
    assert "judge=allow" in result.artifact


def test_no_draft_fact_anchor_falls_back_structural() -> None:
    result = weave_semantic([
        ("a", "plain value one"),
        ("b", "plain value two"),
    ])
    assert result.method == "structural"
    # The honest fallback is a real bundle keyed by capability, not a fake weave.
    assert result.artifact == {"a": "plain value one", "b": "plain value two"}


def test_single_draft_is_still_semantic() -> None:
    result = weave_semantic([("writer", {"draft": "Final: alone."})])
    assert result.method == "semantic"
    assert result.artifact == "Final: alone."


def test_multiple_facts_fold_into_one_draft() -> None:
    result = weave_semantic([
        ("f1", {"fact": "value 1"}),
        ("f2", {"fact": "value 2"}),
        ("d", {"draft": "Final: combined."}),
    ])
    assert result.method == "semantic"
    assert "value 1" in result.artifact and "value 2" in result.artifact


def test_parts_preserve_order() -> None:
    result = weave_semantic([
        ("first", {"fact": "a"}),
        ("second", {"draft": "b"}),
    ])
    assert result.parts == ("first", "second")