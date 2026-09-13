"""Tests for the real archive tool and its connector (second real effect)."""

from __future__ import annotations

import gzip
from pathlib import Path

from universal_mind.archive_adapter import ArchiveToolConnector


def test_compress_produces_a_real_archive() -> None:
    conn = ArchiveToolConnector()
    result = conn.connect({}, {"operation": "compress", "content": "hello world"})
    assert result.ok is True
    assert result.output["bytes"] > 0
    p = Path(result.output["path"])
    assert p.exists()
    # It is a real gzip file that decompresses back to the original payload.
    with gzip.open(p, "rt", encoding="utf-8") as f:
        assert f.read() == "hello world"


def test_unknown_operation_fails_clean() -> None:
    conn = ArchiveToolConnector()
    result = conn.connect({}, {"operation": "nonsense"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_defaults_to_compress_without_operation() -> None:
    conn = ArchiveToolConnector()
    result = conn.connect({}, {})  # no operation -> defaults to compress
    assert result.ok is True
    assert result.output["bytes"] > 0


def test_archive_runs_through_orchestrate_via_factory() -> None:
    """The second real tool (archive) also flows through the synthesis loop."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(
        name="gzip-archive",
        capability="archive",
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
        absorbable=True,
    ))

    def archive_factory(tool: object) -> ArchiveToolConnector:
        return ArchiveToolConnector()

    syn = orchestrate(reg, ["archive"], connector_factory=archive_factory)
    assert syn.ok is True
    assert syn.output["synthesized_from"]["archive"]["bytes"] > 0