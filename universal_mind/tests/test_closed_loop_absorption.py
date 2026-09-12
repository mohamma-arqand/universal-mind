"""Tests for closed-loop absorption (super-platform Phase 2c)."""

from __future__ import annotations

from universal_mind.closed_loop_absorption import ingest_spec
from universal_mind.tool_registry import ToolRegistry


def test_open_spec_absorbs_into_internal_capability() -> None:
    reg = ToolRegistry()
    result = ingest_spec({
        "name": "gimp", "capability": "edit_image", "mechanism": "subprocess",
        "command": "gimp", "absorbable": True,
    }, reg)
    assert result.parsed is True
    assert result.absorbed is True
    assert result.internal_name == "internal:edit_image"
    # The internal capability is registered under the capability slug.
    assert "internal:edit_image" in [t.name for t in reg.tools_for("edit_image")]


def test_closed_spec_is_registered_but_not_absorbed() -> None:
    reg = ToolRegistry()
    result = ingest_spec({
        "name": "excel", "capability": "spreadsheet", "mechanism": "com",
        "prog_id": "Excel.Application",  # absorbable default False
    }, reg)
    assert result.parsed is True
    assert result.absorbed is False
    assert result.internal_name == ""
    # Still registered (connected), just not re-implemented.
    assert reg.capable("spreadsheet")


def test_malformed_spec_is_refused() -> None:
    reg = ToolRegistry()
    result = ingest_spec({"name": "broken"}, reg)
    assert result.parsed is False
    assert "missing required field" in result.error
    assert result.absorbed is False


def test_pipeline_runs_end_to_end_for_multiple_tools() -> None:
    from typing import Any

    reg = ToolRegistry()
    specs: list[dict[str, Any]] = [
        {"name": "ffmpeg", "capability": "transcode", "mechanism": "subprocess", "command": "ffmpeg", "absorbable": True},
        {"name": "gmail", "capability": "send_email", "mechanism": "http", "endpoint": "http://x", "absorbable": True},
        {"name": "excel", "capability": "spreadsheet", "mechanism": "com", "prog_id": "Excel.Application"},
    ]
    results = [ingest_spec(s, reg) for s in specs]
    assert all(r.parsed for r in results)
    assert sum(1 for r in results if r.absorbed) == 2  # only the two open tools absorbed
    assert reg.capable("transcode") and reg.capable("send_email") and reg.capable("spreadsheet")