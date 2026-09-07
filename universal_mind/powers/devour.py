"""Devour power: absorb an external tool into the registry.

Spec concept: The ability to discover, wrap, and register an external tool
(API, CLI, library) as a first-class capability in the pantheon registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..pantheon.contracts import Capability
from ..pantheon.registry import CapabilityDossier


@dataclass(frozen=True)
class ToolDescriptor:
    """Description of an external tool to be devoured."""
    name: str
    tool_type: str  # "api", "cli", "library", "mcp", "openapi"
    entry_point: str  # URL, command, import path, etc.
    auth_config: dict[str, Any] | None = None
    schema: dict[str, Any] | None = None  # OpenAPI, JSON schema, etc.
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class DevourInput:
    """Input for devouring a tool."""
    tool: ToolDescriptor
    owner_id: str
    auto_register: bool = True


@dataclass(frozen=True)
class DevourOutput:
    """Output from devouring a tool."""
    capability: Capability
    dossier: CapabilityDossier
    wrapper_code: str | None = None
    warnings: list[str] | None = None


@runtime_checkable
class Devour(Protocol):
    """Protocol for absorbing external tools into the capability registry.

    The Devour power discovers, wraps, and registers external tools
    as first-class capabilities with full dossiers.
    """

    async def devour(self, input: DevourInput) -> DevourOutput:
        """Absorb an external tool into the registry.

        Args:
            input: DevourInput with tool descriptor, owner_id, auto_register

        Returns:
            DevourOutput with capability, dossier, wrapper code
        """
        ...


class InMemoryDevour:
    """Reference in-memory implementation of Devour (no I/O).

    Generates a simple wrapper and dossier for the tool.
    """

    def __init__(self) -> None:
        self._devoured: dict[str, DevourOutput] = {}

    async def devour(self, input: DevourInput) -> DevourOutput:
        tool = input.tool
        warnings: list[str] = []

        # Generate capability wrapper code
        wrapper_code = self._generate_wrapper(tool)

        # Create dossier
        dossier = CapabilityDossier(
            name=tool.name,
            version="1.0.0",
            signature=f"({tool.tool_type}) -> Any",
            purpose=f"Devoured {tool.tool_type} tool: {tool.name}",
            cost_model="unknown",
            latency_profile="unknown",
            reliability="unknown",
            side_effects="external",
            reversible=False,
            required_secrets=list((tool.auth_config or {}).keys()),
            failure_modes="External tool may fail, timeout, or return errors",
            dependencies=[],
            determinism=__import__('universal_mind.core.intent', fromlist=['Determinism']).Determinism.STRICT,
            provenance={
                "owner_id": input.owner_id,
                "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                "source": "devour",
                "tool_type": tool.tool_type,
                "entry_point": tool.entry_point,
            },
            idempotent=False,
        )

        # Create a minimal capability
        class DevouredCapability(Capability):
            async def execute(self, intent, params):
                return {"status": "devoured_stub", "tool": tool.name}

            def validate_intent(self, intent: object) -> None:
                pass

        capability = DevouredCapability()

        output = DevourOutput(
            capability=capability,
            dossier=dossier,
            wrapper_code=wrapper_code,
            warnings=warnings if warnings else None,
        )

        if input.auto_register:
            self._devoured[tool.name] = output

        return output

    def _generate_wrapper(self, tool: ToolDescriptor) -> str:
        """Generate wrapper code for the tool."""
        if tool.tool_type == "cli":
            return f'''async def {tool.name}_wrapper(argv: list[str]) -> dict:
    import subprocess
    result = subprocess.run(["{tool.entry_point}"] + argv, capture_output=True, text=True)
    return {{"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}}'''
        elif tool.tool_type == "api":
            return f'''async def {tool.name}_wrapper(method: str, path: str, **kwargs) -> dict:
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.request(method, "{tool.entry_point}" + path, **kwargs) as resp:
            return await resp.json()'''
        elif tool.tool_type == "library":
            return f'''async def {tool.name}_wrapper(*args, **kwargs) -> Any:
    import importlib
    mod = importlib.import_module("{tool.entry_point}")
    return await mod.main(*args, **kwargs)'''
        else:
            return f"# Wrapper for {tool.name} ({tool.tool_type}) - implementation needed"