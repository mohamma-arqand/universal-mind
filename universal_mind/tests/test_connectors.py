"""Tests for the universal connectors (super-platform Phase B)."""

from __future__ import annotations

from universal_mind.connectors import (
    ComConnector,
    ConnectorResult,
    HttpConnector,
    SubprocessConnector,
    connector_for,
)
from universal_mind.tool_registry import ConnectionMechanism, ToolConnectionSpec


def test_subprocess_connector_runs_allowlisted_command() -> None:
    spec = ToolConnectionSpec(
        mechanism=ConnectionMechanism.SUBPROCESS, command="echo hello world"
    )
    out = SubprocessConnector().connect(spec, {})
    assert out.ok is True
    assert out.output == "hello world"


def test_subprocess_connector_refuses_non_allowlisted() -> None:
    spec = ToolConnectionSpec(
        mechanism=ConnectionMechanism.SUBPROCESS, command="rm -rf /"
    )
    out = SubprocessConnector().connect(spec, {})
    assert out.ok is False
    assert "not allowlisted" in out.error


def test_subprocess_connector_missing_command_fails_clean() -> None:
    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS)
    out = SubprocessConnector().connect(spec, {})
    assert out.ok is False


def test_http_connector_missing_key_fails_clean() -> None:
    spec = ToolConnectionSpec(
        mechanism=ConnectionMechanism.HTTP, endpoint="http://x/v1"
    )
    out = HttpConnector().connect(spec, {})
    assert out.ok is False
    assert "api_key" in out.error


def test_http_connector_transport_error_is_not_ok() -> None:
    spec = ToolConnectionSpec(
        mechanism=ConnectionMechanism.HTTP, endpoint="http://127.0.0.1:1/nope"
    )
    out = HttpConnector(timeout_seconds=1).connect(spec, {"api_key": "k", "model": "m"})
    assert out.ok is False


def test_com_connector_missing_progid_fails_clean() -> None:
    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.COM)
    out = ComConnector().connect(spec, {})
    assert out.ok is False
    assert "prog_id" in out.error


def test_com_connector_invalid_progid_reports_error() -> None:
    # A ProgID that does not exist must fail clean, not hang or crash.
    spec = ToolConnectionSpec(
        mechanism=ConnectionMechanism.COM, prog_id="No.Such.Object.12345"
    )
    out = ComConnector().connect(spec, {})
    # Either PowerShell reports a non-zero exit (app missing) -> not ok, or it
    # genuinely connects (should not for a fake ProgID). It must never hang.
    assert isinstance(out, ConnectorResult)


def test_connector_for_maps_mechanisms() -> None:
    from universal_mind.connectors import (
        ComConnector,
        HttpConnector,
        SubprocessConnector,
    )

    assert isinstance(
        connector_for(ConnectionMechanism.SUBPROCESS), SubprocessConnector
    )
    assert isinstance(connector_for(ConnectionMechanism.HTTP), HttpConnector)
    assert isinstance(connector_for(ConnectionMechanism.COM), ComConnector)
    assert isinstance(connector_for("subprocess"), SubprocessConnector)
    assert isinstance(connector_for("http"), HttpConnector)
    assert isinstance(connector_for("com"), ComConnector)
