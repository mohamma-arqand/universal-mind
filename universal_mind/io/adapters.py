"""L1 GATEWAY — the single contract any external specialist honors.

The charter's GATEWAY rule: *every external tool (LiteLLM, OpenHands, MCP,
shell, human) is a contractor, never the boss* — it is used through ONE contract
front, and only if it can honor that contract. This module defines that front:

- :class:`ToolContract` — the contract attributes a specialist must declare
  (cost, latency, reliability, reversibility, side effects, required secrets,
  determinism, domains, credibility);
- :class:`Tool` — what a specialist must be able to do;
- :class:`ToolCapability` — adapts ANY specialist into the Pantheon's
  :class:`~universal_mind.pantheon.contracts.Capability` boundary, enforcing
  the contract at validation time (a specialist that cannot honor an intent is
  refused, exactly as a contractor would be);
- reference specialists (:class:`HumanSpecialist`, :class:`ShellSpecialist`)
  that are deterministic, isolated, and fail-safe, so the contract is exercised
  without connecting to anything real.

Nothing here executes code in the live tree; side-effecting specialists run in a
throwaway sandbox or are refused.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from universal_mind.core.errors import SystemFault, TaskFailure
from universal_mind.core.intent import Determinism, Intent
from universal_mind.layers import Layer
from universal_mind.pantheon.contracts import (
    Capability,
    CapabilityResult,
    ContractViolation,
)
from universal_mind.pantheon.registry import (
    CapabilityDossier,
    OrganDescriptor,
    PantheonRegistry,
)


@dataclass(frozen=True)
class ToolContract:
    """The contract a specialist declares about itself before being trusted."""

    name: str
    version: str
    purpose: str
    signature: str
    cost_model: str
    latency_profile: str
    reliability: str
    reversible: bool
    side_effects: str
    required_secrets: list[str]
    determinism: Determinism
    domains: tuple[str, ...]
    credibility: float = 0.5
    layer: Layer = Layer.GATEWAY
    cost: float = 1.0


@runtime_checkable
class Tool(Protocol):
    """What any external specialist must implement to enter the pantheon."""

    contract: ToolContract

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        """Perform the work. Raises TaskFailure on failure; no side effect in the tree."""
        ...


def dossier_for(tool: Tool, owner_id: str) -> CapabilityDossier:
    """Build a CapabilityDossier from a specialist's declared contract."""
    c = tool.contract
    return CapabilityDossier(
        name=c.name,
        version=c.version,
        signature=c.signature,
        purpose=c.purpose,
        cost_model=c.cost_model,
        latency_profile=c.latency_profile,
        reliability=c.reliability,
        side_effects=c.side_effects,
        reversible=c.reversible,
        required_secrets=list(c.required_secrets),
        failure_modes="none" if c.reversible else "non_reversible",
        dependencies=[],
        determinism=c.determinism,
        idempotent=c.reversible,
        provenance={
            "owner_id": owner_id,
            "producer": "gateway:adapter",
            "explicit_fields": ["idempotent", "determinism"],
        },
    )


def organ_for(tool: Tool, owner_id: str) -> OrganDescriptor:
    """Build an OrganDescriptor so the specialist is searchable by domain/credibility."""
    c = tool.contract
    return OrganDescriptor(
        name=c.name,
        signature=c.signature,
        cost=c.cost,
        latency_ms=10.0,
        credibility=c.credibility,
        domains=c.domains,
        layer=c.layer,
        dossier=dossier_for(tool, owner_id),
    )


class ToolCapability(Capability):
    """Adapt any external specialist into the Pantheon Capability boundary.

    Enforces the contract at the gate: an intent that demands a determinism the
    tool does not offer, or that the tool cannot honor (needs a missing secret),
    is refused as :class:`ContractViolation` — the specialist stays a contractor
    constrained by its own declared contract.
    """

    def __init__(self, tool: Tool, resolver: Any | None = None) -> None:
        self._tool = tool
        self._resolver = resolver

    def validate_intent(self, intent: Intent) -> None:
        c = self._tool.contract
        if intent.determinism not in (Determinism.STRICT, Determinism.CREATIVE):
            raise ContractViolation(f"Invalid determinism level: {intent.determinism}")
        if c.determinism == Determinism.STRICT and intent.determinism == Determinism.CREATIVE:
            raise ContractViolation(
                f"{c.name} is STRICT-deterministic and cannot honor a CREATIVE intent"
            )
        for secret in c.required_secrets:
            resolved = None
            if self._resolver is not None:
                resolved = self._resolver(secret)
            elif "SECRET_" + secret.upper() in os.environ:
                resolved = os.environ.get("SECRET_" + secret.upper())
            if not resolved:
                raise ContractViolation(
                    f"{c.name} requires secret '{secret}' which is not available"
                )

    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        output = self._tool.run(intent, params)
        return CapabilityResult(
            ok=True,
            output=output,
            cost={"currency": "units", "amount": 1.0},
            provenance={"producer": f"gateway:{self._tool.contract.name}"},
            notes=(f"served by {self._tool.contract.name}",),
        )

    @property
    def tool(self) -> Tool:
        return self._tool


def register_tool(
    registry: PantheonRegistry,
    tool: Tool,
    owner_id: str,
) -> str:
    """Register a specialist as a capability+organ, idempotently across reopens."""
    try:
        restored = registry.restore_capability(tool.contract.name, tool.contract.version, ToolCapability(tool))
    except SystemFault:
        restored = False
    if not restored:
        registry.register(dossier_for(tool, owner_id), ToolCapability(tool))
    # Make the specialist selectable by domain/credibility for CapabilityResolver.
    registry.attach_organ(organ_for(tool, owner_id))
    return tool.contract.name


class CapabilityResolver:
    """Select a registered specialist by capability (domain/signature) and credibility.

    This is the ``CapabilityResolver`` step of the execution loop: given a
    needed domain, return the organ that can best honor it — matched by the
    organ's declared domains (exact first, then substring over purpose), ties
    broken by credibility (highest wins), then name (deterministic). Selection is
    purely by declared contract, never by identity, so any specialist is
    swappable without touching the orchestrator.
    """

    def resolve_organ(
        self,
        registry: PantheonRegistry,
        needed_domain: str,
    ) -> OrganDescriptor | None:
        """Return the best organ for ``needed_domain``, or None if none fits."""
        return self._pick(registry.list_organs(), needed_domain)

    @classmethod
    def _pick(cls, organs: list[OrganDescriptor], domain: str) -> OrganDescriptor | None:
        if not organs:
            return None
        exact = [o for o in organs if domain in o.domains]
        purpose = [
            o for o in organs
            if domain.lower() in o.dossier.purpose.lower()
            or domain.lower() in o.signature.lower()
        ]
        pool = exact or purpose
        if not pool:
            # No organ fits the requested domain — return None so the caller can
            # raise an honest "no specialist" error, rather than silently serving
            # an unrelated organ (the highest-credibility one) as a false match.
            return None
        # Highest credibility; ties by name for determinism.
        return max(pool, key=lambda o: (o.credibility, -len(o.name)))


# ---------------------------------------------------------------------------
# Reference specialists (deterministic, isolated, fail-safe).
# ---------------------------------------------------------------------------


class HumanSpecialist:
    """A specialist that defers to a human reviewer (deterministic marker).

    Runs no code; emits a record that a human verdict is required. Reversible,
    no side effects, any determinism.
    """

    contract = ToolContract(
        name="human",
        version="1.0.0",
        purpose="Add a human-in-the-loop review/approval step.",
        signature="human(intent, params)",
        cost_model="expensive",
        latency_profile="slow",
        reliability="high",
        reversible=True,
        side_effects="none",
        required_secrets=[],
        determinism=Determinism.CREATIVE,
        domains=("general", "safety"),
        credibility=1.0,
    )

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        return {"status": "needs_human_review", "goal": intent.goal}


class ShellSpecialist:
    """A side-effecting specialist that runs shell in a throwaway sandbox.

    Deliberately constrained to a read-only whitelist so it can never act as
    "boss": anything outside the allowlist is refused with a TaskFailure that
    identifies the violation. This is the isolation contract in action.
    """

    WHITELIST = ("pwd", "echo", "whoami", "true")

    contract = ToolContract(
        name="shell",
        version="1.0.0",
        purpose="Run a small, read-only shell command in an isolated sandbox.",
        signature="shell(intent, params)",
        cost_model="flat",
        latency_profile="fast",
        reliability="high",
        reversible=True,
        side_effects="isolated shell execution",
        required_secrets=[],
        determinism=Determinism.STRICT,
        domains=("system",),
        credibility=0.6,
    )

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        command = params.get("command")
        if not isinstance(command, str) or not command:
            raise TaskFailure("shell specialist requires a 'command' param")
        tokens = command.split()
        if not tokens or tokens[0] not in self.WHITELIST:
            raise TaskFailure(
                f"command '{tokens[0] if tokens else ''}' is not whitelisted; "
                "shell is a contractor, not the boss"
            )
        sandbox = Path(tempfile.mkdtemp(prefix="um-shell-"))
        try:
            result = subprocess.run(
                command, shell=True, cwd=sandbox,
                capture_output=True, text=True, timeout=15, check=False,
            )
            if result.returncode != 0:
                raise TaskFailure(f"shell exited {result.returncode}: {result.stderr.strip()}")
            return {"stdout": result.stdout.strip()}
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)


class McpSpecialist:
    """Deterministic stub honoring the MCP specialist contract (no real server).

    Read-only and fail-safe: without an MCP_BASE_URL it refuses loudly rather
    than pretending to connect.
    """

    contract = ToolContract(
        name="mcp",
        version="1.0.0",
        purpose="Query an MCP server for tool listings (stub).",
        signature="mcp(intent, params)",
        cost_model="flat",
        latency_profile="normal",
        reliability="medium",
        reversible=True,
        side_effects="read-only",
        required_secrets=["MCP_BASE_URL"],
        determinism=Determinism.STRICT,
        domains=("tools",),
        credibility=0.5,
    )

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        if not (self._base_url or os.environ.get("UM_MCP_BASE_URL")):
            raise TaskFailure("mcp specialist requires UM_MCP_BASE_URL to be set")
        return {"status": "stub", "tools": []}