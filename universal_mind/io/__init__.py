"""GATEWAY layer (Layer 1): adapters to external systems.

The ``io`` package connects capabilities to real providers (LLM/HTTP) behind a
small, deterministic surface: a :class:`Provider` protocol, reference providers
(Echo, Scripted), an OpenAI-compatible :class:`HttpChatProvider`, and a
:class:`Gateway` that retries with backoff and fails over across an ordered
provider list. API keys are resolved lazily through a
:class:`SecretResolver` and never stored or logged.
"""

from __future__ import annotations

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
    Provider,
    ProviderResult,
    ScriptedProvider,
    env_resolver,
)

__all__ = [
    "EchoProvider",
    "Gateway",
    "GatewayOutcome",
    "HttpChatProvider",
    "Message",
    "Provider",
    "ProviderConfig",
    "ProviderError",
    "ProviderPermanent",
    "ProviderResult",
    "ProviderTransient",
    "ScriptedProvider",
    "env_resolver",
]