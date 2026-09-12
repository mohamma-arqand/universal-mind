"""Tests for orchestrated synthesis (super-platform Phase D)."""

from __future__ import annotations

from universal_mind.orchestration import SubOutput, orchestrate
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str, command: str = "echo hello") -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=command),
        absorbable=True,
    )


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(_entry("a", "transcode", "echo transcode_out"))
    reg.register(_entry("b", "send_email", "echo email_out"))
    return reg


def test_orchestrate_fuses_multiple_tools_into_one_artifact() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode", "send_email"])
    assert syn.ok is True
    # D is a single fused artifact keyed by capability, produced by NO single tool.
    assert syn.output["synthesized_from"]["transcode"] == "transcode_out"
    assert syn.output["synthesized_from"]["send_email"] == "email_out"
    assert len(syn.sub_outputs) == 2


def test_missing_capability_fails_the_whole_synthesis() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode", "nonexistent_capability"])
    assert syn.ok is False
    # The missing capability is an explicit failed sub-output, not a fake result.
    missing = [s for s in syn.sub_outputs if s.ok is False]
    assert len(missing) == 1
    assert missing[0].capability == "nonexistent_capability"
    assert "no tool" in missing[0].error


def test_injectable_composer_controls_the_fusion() -> None:
    reg = _registry()

    def join(sub_outputs: list[SubOutput]) -> str:
        return " + ".join(str(s.output) for s in sub_outputs if s.ok)

    syn = orchestrate(reg, ["transcode", "send_email"], composer=join)
    assert syn.output == "transcode_out + email_out"


def test_single_capability_is_still_a_synthesis() -> None:
    reg = _registry()
    syn = orchestrate(reg, ["transcode"])
    assert syn.ok is True
    assert syn.output["synthesized_from"]["transcode"] == "transcode_out"


def test_best_tool_is_chosen_by_evidence() -> None:
    reg = ToolRegistry()
    rookie = _entry("rookie", "transcode", "echo rookie_out")
    proven = _entry("proven", "transcode", "echo proven_out")
    proven.record_evidence(True, 1.0)
    reg.register(rookie)
    reg.register(proven)
    syn = orchestrate(reg, ["transcode"])
    # The proven tool (higher evidence) is the one reached.
    assert syn.sub_outputs[0].tool_name == "proven"
    assert syn.output["synthesized_from"]["transcode"] == "proven_out"


def test_orchestration_records_evidence_on_tools() -> None:
    reg = _registry()
    orchestrate(reg, ["transcode", "send_email"])
    # Each tool now carries one evidence point from this run (feeds Phase E).
    for tool in reg.tools_for("transcode") + reg.tools_for("send_email"):
        assert len(tool.evidence) == 1