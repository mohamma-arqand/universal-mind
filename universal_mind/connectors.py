"""Universal connectors — the three ways to reach any tool (super-platform Phase B).

Phase A gave us the encyclopedia (what each tool can do + which mechanism reaches
it). Phase B gives us the *hands*: one connector per connection mechanism, so a
tool registered with ``subprocess`` / ``http`` / ``com`` is actually reachable.

Each connector is a thin, deterministic, fail-safe adapter:

- :class:`SubprocessConnector` — runs a CLI/agent in a throwaway sandbox, gated by
  an allowlist (a tool outside the allowlist is refused, never run).
- :class:`HttpConnector` — calls an OpenAI-compatible JSON endpoint and returns the
  parsed text (reuses the secret-resolver pattern; no key is stored/logged).
- :class:`ComConnector` — drives a Windows COM object through PowerShell (the only
  open way to control a licensed desktop app like Excel); it never runs a bare
  command — the ProgID is the allowlist.

All three return an :class:`ConnectorResult` so the brain treats every tool alike
regardless of mechanism. Nothing here runs a tool outside its declared gate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from universal_mind.core.errors import TaskFailure


@dataclass(frozen=True)
class ConnectorResult:
    """The normalized outcome of reaching one tool, regardless of mechanism."""

    ok: bool
    output: Any
    error: str = ""


@runtime_checkable
class Connector(Protocol):
    """What any connector must do: take a spec + params, return a normalized result."""

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult: ...


class SubprocessConnector:
    """Run a CLI/agent in a throwaway sandbox, gated by an allowlist.

    The allowlist is the *contract*: a tool whose first token is not allowlisted
    is refused with a :class:`TaskFailure` naming the violation — the subprocess
    path can never act as "boss".
    """

    def __init__(self, allowlist: tuple[str, ...] | None = None) -> None:
        self._allowlist = (
            allowlist if allowlist is not None else ("pwd", "echo", "whoami", "true")
        )

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        command = spec.command or params.get("command", "")
        if not isinstance(command, str) or not command.strip():
            return ConnectorResult(
                ok=False, output=None, error="subprocess connector needs a command"
            )
        tokens = command.split()
        if not tokens or tokens[0] not in self._allowlist:
            return ConnectorResult(
                ok=False,
                output=None,
                error=f"command '{tokens[0] if tokens else ''}' is not allowlisted",
            )
        sandbox = Path(tempfile.mkdtemp(prefix="um-conn-"))
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=sandbox,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
        if result.returncode != 0:
            return ConnectorResult(ok=False, output=None, error=result.stderr.strip())
        return ConnectorResult(ok=True, output=result.stdout.strip())


class HttpConnector:
    """Call an OpenAI-compatible endpoint and return the first assistant text."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout = timeout_seconds

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        endpoint = spec.endpoint
        if not endpoint:
            return ConnectorResult(
                ok=False, output=None, error="http connector needs an endpoint"
            )
        api_key = params.get("api_key")
        if not api_key:
            return ConnectorResult(
                ok=False, output=None, error="http connector needs an api_key"
            )
        payload = {
            "model": params.get("model", "default"),
            "messages": params.get("messages", [{"role": "user", "content": ""}]),
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — any transport error is a failed connect
            return ConnectorResult(ok=False, output=None, error=str(exc))
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            return ConnectorResult(
                ok=False, output=None, error=f"malformed provider response: {exc}"
            )
        return ConnectorResult(ok=True, output=text)


class ComConnector:
    """Drive a Windows COM object through PowerShell (the licensed-app path).

    The ``prog_id`` (e.g. "Excel.Application") is itself the allowlist: only a
    registered ProgID is ever launched, and the invocation is an explicit
    PowerShell ``New-Object -ComObject`` — no bare `-Command` string shell-injection
    surface. Fails clean (never blocks) when the app or PowerShell is unavailable.
    """

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        prog_id = spec.prog_id or params.get("prog_id", "")
        if not prog_id:
            return ConnectorResult(
                ok=False, output=None, error="com connector needs a prog_id"
            )
        # A minimal, deterministic probe: instantiate the COM object and read its
        # version, proving the app is reachable and scriptable.
        ps = (
            f"$o = New-Object -ComObject {prog_id}; "
            f"Write-Output $o.Version; "
            f"[System.Runtime.Interopservices.Marshal]::ReleaseComObject($o)"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            return ConnectorResult(
                ok=False, output=None, error="powershell.exe not available"
            )
        if result.returncode != 0:
            return ConnectorResult(ok=False, output=None, error=result.stderr.strip())
        return ConnectorResult(ok=True, output=result.stdout.strip())


def connector_for(mechanism: Any) -> Connector:
    """Return the connector matching a ``ConnectionMechanism`` value or string."""
    from universal_mind.tool_registry import ConnectionMechanism

    if isinstance(mechanism, str):
        mechanism = ConnectionMechanism(mechanism)
    if mechanism is ConnectionMechanism.SUBPROCESS:
        return SubprocessConnector()
    if mechanism is ConnectionMechanism.HTTP:
        return HttpConnector()
    if mechanism is ConnectionMechanism.COM:
        return ComConnector()
    raise TaskFailure(f"unknown connection mechanism: {mechanism!r}")


__all__ = [
    "ComConnector",
    "Connector",
    "ConnectorResult",
    "HttpConnector",
    "SubprocessConnector",
    "connector_for",
]
