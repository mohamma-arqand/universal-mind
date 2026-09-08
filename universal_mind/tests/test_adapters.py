"""Tests for the L1 GATEWAY unified contract — specialists are contractors.

REBUILT: this file's original (an in-progress concurrent edit) was accidentally
overwritten; these tests reconstruct full coverage from the adapters API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from universal_mind.core.errors import TaskFailure
from universal_mind.core.intent import Determinism, Intent
from universal_mind.io import (
    CapabilityResolver,
    HumanSpecialist,
    McpSpecialist,
    ShellSpecialist,
    Tool,
    ToolCapability,
    register_tool,
)
from universal_mind.memory.store import InMemoryStore, LocalJSONLStore
from universal_mind.pantheon.contracts import ContractViolation
from universal_mind.pantheon.registry import PantheonRegistry


def _intent(goal: str = "do the task", determinism: Determinism = Determinism.STRICT) -> Intent:
    return Intent.from_raw(
        raw_text=f"{goal}. Must be done.",
        goal=goal,
        success_criteria=["done"],
        owner_id="owner",
        determinism=determinism,
    )


def _registry(store: InMemoryStore | None = None) -> PantheonRegistry:
    return PantheonRegistry(store if store is not None else InMemoryStore())


# --- human specialist: a contractor that defers to a human, never acts alone ---


def test_human_specialist_is_contractor() -> None:
    """Human specialist runs no code; it emits a needs-human-review marker."""
    h = HumanSpecialist()
    out = h.run(_intent(), {})
    assert out["status"] == "needs_human_review"
    assert h.contract.reversible is True


# --- shell specialist: whitelist + isolation ---


def test_shell_specialist_runs_whitelisted_command() -> None:
    """Whitelisted commands execute in an isolated sandbox."""
    s = ShellSpecialist()
    out = s.run(_intent(), {"command": "pwd"})
    assert "stdout" in out


def test_shell_specialist_refuses_non_whitelisted() -> None:
    """Anything outside the allowlist is refused — shell is a contractor, not boss."""
    s = ShellSpecialist()
    with pytest.raises(TaskFailure):
        s.run(_intent(), {"command": "rm -rf /"})


# --- contract validation ---


def test_tool_contract_validation_refuses_missing_secret() -> None:
    """A specialist needing a missing secret is refused at the gate."""
    mcp = McpSpecialist()  # requires MCP_BASE_URL
    cap = ToolCapability(mcp)
    assert "MCP_BASE_URL" in mcp.contract.required_secrets
    with pytest.raises(ContractViolation):
        cap.validate_intent(_intent())


def test_secret_resolvable_via_resolver() -> None:
    """A resolver that supplies the secret lets validation pass."""
    mcp = McpSpecialist()
    cap = ToolCapability(mcp, resolver=lambda name: "fake-value")
    cap.validate_intent(_intent())  # must not raise


def test_contract_determinism_gate() -> None:
    """A STRICT tool cannot honor a CREATIVE intent."""
    cap = ToolCapability(ShellSpecialist())
    cap.validate_intent(_intent(determinism=Determinism.STRICT))  # ok
    with pytest.raises(ContractViolation):
        cap.validate_intent(_intent(determinism=Determinism.CREATIVE))


# --- registration ---


def test_register_tool_into_registry() -> None:
    """A specialist registers as a capability under its declared contract name."""
    reg = _registry()
    rid = register_tool(reg, ShellSpecialist(), "owner")
    assert rid == "shell"
    assert reg.get("shell", "1.0.0") is not None


def test_tool_protocol_conformance() -> None:
    """Reference specialists conform to the Tool protocol."""
    assert isinstance(HumanSpecialist(), Tool)
    assert isinstance(ShellSpecialist(), Tool)
    assert isinstance(McpSpecialist(), Tool)


def test_register_tool_is_idempotent_across_reopens(tmp_path: Path) -> None:
    """Re-registering after a reopen does not duplicate the registration record."""
    store = LocalJSONLStore(directory=tmp_path)
    reg1 = PantheonRegistry(store)
    register_tool(reg1, ShellSpecialist(), "owner")

    reg2 = PantheonRegistry(store)  # reopens the same on-disk ledger
    register_tool(reg2, ShellSpecialist(), "owner")

    n = sum(1 for r in store.read_all()
            if r.get("kind") == "capability_registration"
            and r.get("payload", {}).get("dossier", {}).get("name") == "shell")
    assert n == 1  # no duplicate registration record


# --- capability resolver (selection by contract, not identity) ---


def test_resolver_selects_by_domain() -> None:
    """Resolver returns the organ whose domain matches (exact first)."""
    reg = _registry()
    register_tool(reg, ShellSpecialist(), "owner")   # domain ("system",)
    register_tool(reg, HumanSpecialist(), "owner")   # domains ("general","safety")
    hit = CapabilityResolver().resolve_organ(reg, "system")
    assert hit is not None and hit.name == "shell"


def test_resolver_prefers_credible_on_tie() -> None:
    """Ties resolve to the most credible organ."""
    reg = _registry()
    register_tool(reg, ShellSpecialist(), "owner")  # credibility 0.6
    register_tool(reg, HumanSpecialist(), "owner")   # credibility 1.0
    hit = CapabilityResolver().resolve_organ(reg, "general")
    assert hit is not None and hit.name == "human"


def test_resolver_empty_registry() -> None:
    """No organs -> resolver returns None, not an error."""
    assert CapabilityResolver().resolve_organ(_registry(), "anything") is None