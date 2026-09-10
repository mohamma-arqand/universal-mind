"""GATEWAY layer (Layer 1): adapters to external systems.

The ``io`` package connects capabilities to real providers (LLM/HTTP) behind a
small, deterministic surface: a :class:`Provider` protocol, reference providers
(Echo, Scripted), an OpenAI-compatible :class:`HttpChatProvider`, and a
:class:`Gateway` that retries with backoff and fails over across an ordered
provider list. API keys are resolved lazily through a
:class:`SecretResolver` and never stored or logged.
"""

from __future__ import annotations

from universal_mind.io.adapters import (
    CapabilityResolver,
    HumanSpecialist,
    McpSpecialist,
    ShellSpecialist,
    Tool,
    ToolCapability,
    ToolContract,
    dossier_for,
    organ_for,
    register_tool,
)
from universal_mind.io.errors import (
    ProviderConfig,
    ProviderError,
    ProviderPermanent,
    ProviderTransient,
)
from universal_mind.io.gateway import (
    EchoProvider,
    Gateway,
    GatewayOutcome,
    HttpChatProvider,
    Message,
    MessagePart,
    Provider,
    ProviderResult,
    ScriptedProvider,
    env_resolver,
)
from universal_mind.io.stub_server import StubChatServer

__all__ = [
    "CapabilityResolver",
    "EchoProvider",
    "Gateway",
    "GatewayOutcome",
    "HttpChatProvider",
    "HumanSpecialist",
    "McpSpecialist",
    "Message",
    "MessagePart",
    "Provider",
    "ProviderConfig",
    "ProviderError",
    "ProviderPermanent",
    "ProviderResult",
    "ProviderTransient",
    "ScriptedProvider",
    "ShellSpecialist",
    "StubChatServer",
    "Tool",
    "ToolCapability",
    "ToolContract",
    "dossier_for",
    "env_resolver",
    "organ_for",
    "register_tool",
]