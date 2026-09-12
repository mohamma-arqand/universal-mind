"""Tests for spec introspection (super-platform Phase 2b)."""

from __future__ import annotations

from universal_mind.spec_introspection import read_spec
from universal_mind.tool_registry import ConnectionMechanism


def test_parses_a_complete_subprocess_spec() -> None:
    reading = read_spec({
        "name": "ffmpeg",
        "capability": "transcode",
        "mechanism": "subprocess",
        "command": "ffmpeg -i in.mp4 out.mp4",
        "absorbable": True,
    })
    assert reading.error == ""
    assert reading.entry is not None
    assert reading.entry.capability == "transcode"
    assert reading.entry.connection_mechanism is ConnectionMechanism.SUBPROCESS
    assert reading.entry.absorbable is True


def test_parses_http_and_com_specs() -> None:
    http = read_spec({"name": "gmail", "capability": "send_email", "mechanism": "http", "endpoint": "http://x/v1"})
    assert http.entry is not None
    assert http.entry.connection_mechanism is ConnectionMechanism.HTTP

    com = read_spec({"name": "excel", "capability": "spreadsheet", "mechanism": "com", "prog_id": "Excel.Application"})
    assert com.entry is not None
    assert com.entry.connection_mechanism is ConnectionMechanism.COM


def test_missing_required_field_is_refused_not_guessed() -> None:
    reading = read_spec({"name": "ffmpeg"})  # no capability, no mechanism
    assert reading.entry is None
    assert "missing required field" in reading.error


def test_unknown_mechanism_is_refused() -> None:
    reading = read_spec({"name": "x", "capability": "y", "mechanism": "quantum"})
    assert reading.entry is None
    assert "unknown mechanism" in reading.error


def test_absorbable_defaults_to_false() -> None:
    reading = read_spec({"name": "x", "capability": "y", "mechanism": "subprocess", "command": "echo"})
    assert reading.entry is not None
    assert reading.entry.absorbable is False  # closed unless declared open


def test_missing_command_warns_but_parses() -> None:
    reading = read_spec({"name": "x", "capability": "y", "mechanism": "subprocess"})
    assert reading.entry is not None
    assert any("no command" in w for w in reading.warnings)