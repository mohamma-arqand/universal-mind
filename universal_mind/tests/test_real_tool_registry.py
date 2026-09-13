"""Tests for the unified real-tool registry (three real effects, one factory)."""

from __future__ import annotations

from universal_mind.archive_adapter import ArchiveToolConnector
from universal_mind.compute_adapter import ComputeToolConnector
from universal_mind.media_adapter import MediaToolConnector
from universal_mind.orchestration import orchestrate
from universal_mind.real_tool_registry import real_connector_factory
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
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
        absorbable=True,
    )


def test_factory_routes_each_capability_to_the_right_connector() -> None:
    assert isinstance(real_connector_factory(_entry("m", "media")), MediaToolConnector)
    assert isinstance(real_connector_factory(_entry("a", "archive")), ArchiveToolConnector)
    assert isinstance(real_connector_factory(_entry("c", "compute")), ComputeToolConnector)


def test_factory_falls_back_for_unknown_capability() -> None:
    # An unknown capability falls back to the mechanism-derived connector (subprocess).
    from universal_mind.connectors import SubprocessConnector

    entry = _entry("plain", "plain_capability")
    conn = real_connector_factory(entry)
    assert isinstance(conn, SubprocessConnector)


def test_three_real_effects_fuse_in_one_orchestration() -> None:
    reg = ToolRegistry()
    reg.register(_entry("ffmpeg-media", "media"))
    reg.register(_entry("gzip-archive", "archive"))
    reg.register(_entry("node-compute", "compute"))

    syn = orchestrate(reg, ["media", "archive", "compute"], connector_factory=real_connector_factory)
    assert syn.ok is True
    out = syn.output["synthesized_from"]
    # All three real effects produced real results.
    assert out["media"]["bytes"] > 0
    assert out["archive"]["bytes"] > 0
    assert out["compute"] == 4  # default expression 2+2


def test_factory_is_universal_in_orchestrate() -> None:
    """The single factory drives a mixed pipeline: a real tool AND a mechanism tool."""
    reg = ToolRegistry()
    reg.register(_entry("node-compute", "compute"))
    reg.register(ToolEntry(
        name="shell-echo",
        capability="sys",
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="echo hello"),
        absorbable=True,
    ))
    syn = orchestrate(reg, ["compute", "sys"], connector_factory=real_connector_factory)
    assert syn.ok is True
    assert syn.output["synthesized_from"]["compute"] == 4
    assert syn.output["synthesized_from"]["sys"] == "hello"