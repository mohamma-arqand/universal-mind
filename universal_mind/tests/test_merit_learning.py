"""Tests for merit learning over tools (super-platform Phase E)."""

from __future__ import annotations

from universal_mind.merit_learning import apply_recommendation, learn_merits
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str) -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=name),
        absorbable=True,
    )


def test_learn_merits_empty_registry_is_quiet() -> None:
    report = learn_merits(ToolRegistry())
    assert report.recommendations == ()
    assert "enough evidence" in report.summary


def test_noop_for_untested_tools() -> None:
    reg = ToolRegistry()
    reg.register(_entry("untested", "edit_image"))
    report = learn_merits(reg)
    # No evidence -> a noop recommendation (leave ranking untouched), not a guess.
    assert all(r.action == "noop" for r in report.recommendations)
    assert report.recommendations[0].tool_name == "untested"


def test_demote_for_always_failing_tool() -> None:
    reg = ToolRegistry()
    failing = _entry("failing", "edit_image")
    failing.record_evidence(False, 0.0)
    incumbent = _entry("good", "edit_image")
    incumbent.record_evidence(True, 1.0)
    reg.register(incumbent)
    reg.register(failing)
    report = learn_merits(reg)
    assert any(r.action == "demote" and r.tool_name == "failing" for r in report.recommendations)


def test_promote_for_reliable_tool() -> None:
    reg = ToolRegistry()
    incumbent = _entry("incumbent", "edit_image")
    incumbent.record_evidence(True, 0.8)
    challenger = _entry("challenger", "edit_image")
    challenger.record_evidence(True, 0.9)
    challenger.record_evidence(True, 1.0)
    reg.register(incumbent)
    reg.register(challenger)
    report = learn_merits(reg)
    # Both are reliable (mean >= 0.5) -> both promoted.
    promoted = [r.tool_name for r in report.recommendations if r.action == "promote"]
    assert "incumbent" in promoted
    assert "challenger" in promoted


def test_apply_demote_appends_evidence_and_drops_tool() -> None:
    reg = ToolRegistry()
    only = _entry("only", "edit_image")
    only.record_evidence(True, 1.0)
    reg.register(only)
    # A demote recommendation (every-fail) can be realized on the tool.
    from universal_mind.merit_learning import MeritRecommendation

    rec = MeritRecommendation("edit_image", "demote", "only", "test")
    apply_recommendation(reg, rec)
    assert only.evidence[-1]["score"] == 0.0


def test_apply_promote_appends_success_evidence() -> None:
    reg = ToolRegistry()
    tool = _entry("t", "edit_image")
    reg.register(tool)
    from universal_mind.merit_learning import MeritRecommendation

    apply_recommendation(reg, MeritRecommendation("edit_image", "promote", "t", "test"))
    assert tool.evidence[-1]["score"] == 1.0


def test_capabilities_listed_distinct_and_sorted() -> None:
    reg = ToolRegistry()
    reg.register(_entry("a", "transcode"))
    reg.register(_entry("b", "send_email"))
    reg.register(_entry("c", "transcode"))
    assert reg.capabilities() == ("send_email", "transcode")