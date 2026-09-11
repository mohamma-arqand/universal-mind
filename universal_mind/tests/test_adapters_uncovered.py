"""Coverage for io/adapters.py's remaining branches."""

from __future__ import annotations

import os
from typing import Any

import pytest

from universal_mind.core.errors import TaskFailure
from universal_mind.core.intent import Determinism, Intent
from universal_mind.io.adapters import (
    McpSpecialist,
    ShellSpecialist,
    ToolCapability,
    ToolContract,
)
from universal_mind.pantheon.contracts import ContractViolation


def _intent(determinism: Determinism = Determinism.STRICT) -> Intent:
    return Intent(
        raw_text="run", goal="run", success_criteria=["ok"], constraints=[],
        deadline=None, determinism=determinism, owner_id="o",
    )


class _Tool:
    contract = ToolContract(
        name="t", version="1.0.0", purpose="p", signature="t()", cost_model="flat",
        latency_profile="fast", reliability="high", reversible=True,
        side_effects="none", required_secrets=[], determinism=Determinism.STRICT,
        domains=("x",),
    )

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        return "ok"


def test_validate_intent_rejects_non_standard_determinism() -> None:
    cap = ToolCapability(_Tool())
    bad = Intent(
        raw_text="run", goal="run", success_criteria=["ok"], constraints=[],
        deadline=None, determinism="WRONG", owner_id="o",  # type: ignore[arg-type]
    )
    with pytest.raises(ContractViolation):
        cap.validate_intent(bad)


def test_validate_intent_resolves_secret_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SecretTool:
        contract = ToolContract(
            name="t2", version="1.0.0", purpose="p", signature="t2()",
            cost_model="flat", latency_profile="fast", reliability="high",
            reversible=True, side_effects="none", required_secrets=["API_KEY"],
            determinism=Determinism.STRICT, domains=("x",),
        )

        def run(self, intent: Intent, params: dict[str, Any]) -> Any:
            return "ok"

    monkeypatch.setenv("SECRET_API_KEY", "s3cr3t")
    cap = ToolCapability(_SecretTool())  # no resolver -> env fallback
    # should NOT raise: secret resolved from SECRET_API_KEY env
    cap.validate_intent(_intent())


def test_validate_intent_missing_secret_raises() -> None:
    class _SecretTool:
        contract = ToolContract(
            name="t3", version="1.0.0", purpose="p", signature="t3()",
            cost_model="flat", latency_profile="fast", reliability="high",
            reversible=True, side_effects="none", required_secrets=["API_KEY"],
            determinism=Determinism.STRICT, domains=("x",),
        )

        def run(self, intent: Intent, params: dict[str, Any]) -> Any:
            return "ok"

    monkeypatch_env = os.environ
    monkeypatch_env.pop("SECRET_API_KEY", None)
    cap = ToolCapability(_SecretTool())
    with pytest.raises(ContractViolation):
        cap.validate_intent(_intent())


def test_tool_property_returns_wrapped_tool() -> None:
    tool = _Tool()
    cap = ToolCapability(tool)
    assert cap.tool is tool


def test_shell_missing_command_raises() -> None:
    with pytest.raises(TaskFailure):
        ShellSpecialist().run(_intent(), {"command": None})


def test_shell_nonzero_exit_raises() -> None:
    # 'echo' is whitelisted but never fails; to reach the nonzero-exit branch,
    # widen the whitelist to 'sh' (which passes token[0] check) and run a
    # deliberately failing subcommand. `sh -c "exit 3"` exits 3.
    class _FailShell(ShellSpecialist):
        WHITELIST = ("sh",)  # type: ignore[assignment]
        contract = ShellSpecialist.contract

    proc = _FailShell()
    with pytest.raises(TaskFailure):
        proc.run(_intent(), {"command": 'sh -c "exit 3"'})


def test_shell_non_whitelisted_command_raises() -> None:
    with pytest.raises(TaskFailure):
        ShellSpecialist().run(_intent(), {"command": "rm -rf /"})


def test_mcp_without_base_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UM_MCP_BASE_URL", raising=False)
    with pytest.raises(TaskFailure):
        McpSpecialist().run(_intent(), {})


def test_mcp_with_base_url_returns_stub() -> None:
    result = McpSpecialist(base_url="http://x").run(_intent(), {})
    assert result == {"status": "stub", "tools": []}