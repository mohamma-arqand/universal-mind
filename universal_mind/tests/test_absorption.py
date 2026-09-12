"""Tests for absorption (super-platform Phase C)."""

from __future__ import annotations

from universal_mind.absorption import absorb_tool
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str, absorbable: bool) -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=name),
        absorbable=absorbable,
    )


def test_closed_tool_is_never_absorbed() -> None:
    reg = ToolRegistry()
    tool = _entry("photoshop", "edit_image", absorbable=False)
    result = absorb_tool(tool, reg)
    assert result.absorbed is False
    assert "closed" in result.reason
    # Nothing was registered internally.
    assert not any(t.name.startswith("internal:") for t in reg.tools_for("edit_image"))


def test_open_tool_absorbs_into_internal_capability() -> None:
    reg = ToolRegistry()
    tool = _entry("gimp", "edit_image", absorbable=True)
    result = absorb_tool(tool, reg)
    assert result.absorbed is True
    assert result.internal_name == "internal:edit_image"
    # The internal capability now lives in the registry under the capability slug.
    names = [t.name for t in reg.tools_for("edit_image")]
    assert "internal:edit_image" in names


def test_absorbed_capability_is_absorbable_and_evidenced() -> None:
    reg = ToolRegistry()
    result = absorb_tool(_entry("gimp", "edit_image", absorbable=True), reg)
    internal = next(t for t in reg.tools_for("edit_image") if t.name == result.internal_name)
    assert internal.absorbable is True
    assert internal.evidence and internal.evidence[0]["score"] == 1.0
    # The absorbed capability outranks the original (proven record).
    best = reg.best_for("edit_image")
    assert best is not None
    assert best.name == result.internal_name


def test_different_capabilities_absorb_independently() -> None:
    reg = ToolRegistry()
    r1 = absorb_tool(_entry("ffmpeg", "transcode", absorbable=True), reg)
    r2 = absorb_tool(_entry("gmail", "send_email", absorbable=True), reg)
    r3 = absorb_tool(_entry("summarizer", "summarize", absorbable=True), reg)
    r4 = absorb_tool(_entry("excel", "spreadsheet", absorbable=True), reg)
    assert r1.absorbed and r2.absorbed and r3.absorbed and r4.absorbed
    assert reg.capable("transcode")
    assert reg.capable("send_email")
    assert reg.capable("summarize")
    assert reg.capable("spreadsheet")


def test_failed_reimplementation_keeps_connected_tool() -> None:
    reg = ToolRegistry()
    tool = _entry("gimp", "edit_image", absorbable=True)

    def broken_reimpl(entry: ToolEntry) -> tuple[str, object]:
        # A re-implementation that produces the wrong output.
        return "def power(*a, **k):\n    return 'wrong'\n", {"resized": True}

    result = absorb_tool(tool, reg, reimplementer=broken_reimpl)
    assert result.absorbed is False
    assert "failed the benchmark" in result.reason


def test_unknown_capability_still_absorbs_as_echo() -> None:
    # An open tool with a capability outside the known vocabulary still absorbs
    # deterministically (echo behavior) rather than failing outright.
    reg = ToolRegistry()
    result = absorb_tool(_entry("thing", "mystery_capability", absorbable=True), reg)
    assert result.absorbed is True
    assert result.internal_name == "internal:mystery_capability"