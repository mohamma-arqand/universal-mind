"""Gateway: adapters to external providers (LLM / HTTP / stubs).

The GATEWAY layer (``io/``, Layer 1) is where a capability reaches outward to
an actual provider. This module ships:

- lightweight :class:`Message` / :class:`ProviderResult` models;
- a :class:`Provider` protocol, so any external adapter is swappable;
- deterministic reference providers (:class:`EchoProvider`,
  :class:`ScriptedProvider`) used by tests and the self-verifying probe;
- :class:`HttpChatProvider`, an OpenAI-compatible ``/chat/completions`` adapter
  over stdlib ``urllib`` (the "real provider" path), fail-safe when no key is
  configured;
- :class:`Gateway`, which calls a primary provider with retry/backoff and fails
  over to an ordered list of fallback providers.

API keys are never constructed into providers and never logged: they are read
lazily through an injectable :class:`SecretResolver` (default: environment).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from universal_mind.core.errors import RetryPolicy

from .errors import ProviderConfig, ProviderError, ProviderPermanent, ProviderTransient


@dataclass(frozen=True)
class MessagePart:
    """One part of a multimodal message: text, an image, or an audio note.

    ``kind`` is one of ``text``, ``image``, ``audio`` (extensible); ``data``
    carries the part payload. Parts are *additional* to the plain-text
    ``Message.content``, so existing text-only callers are unchanged.
    """

    kind: str
    data: Any


@dataclass(frozen=True)
class Message:
    """A single chat message: plain text with optional multimodal parts.

    ``content`` is the plain-text fallback (always present). ``parts`` may carry
    image/audio/… attachments; a provider that understands only text simply
    ignores parts and uses ``content``, so the contract widens without breaking
    any existing adapter.
    """

    role: str
    content: str
    parts: tuple[MessagePart, ...] = ()


@dataclass(frozen=True)
class ProviderResult:
    """A successful provider response."""

    content: str
    provider_name: str
    cost: float = 0.0


# Resolves a named secret to a value, or None when absent.
SecretResolver = Callable[[str], str | None]


def _serialize_message(message: Message) -> dict[str, Any]:
    """Serialize a :class:`Message` into the OpenAI-compatible wire shape.

    Plain text always rides in ``content``. Any multimodal parts are attached as
    a ``parts`` list (``{kind, data}``) so a provider that understands them can
    pick them up, while a text-only provider just sees ``content``.
    """
    out: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.parts:
        out["parts"] = [{"kind": p.kind, "data": p.data} for p in message.parts]
    return out


def env_resolver(name: str) -> str | None:
    """Default secret resolver: reads from the process environment."""
    return os.environ.get(name)


@runtime_checkable
class Provider(Protocol):
    """A provider able to turn messages into a response.

    Implementations must raise a :class:`ProviderError` subclass on failure;
    on success they return a :class:`ProviderResult`. Providers must not embed
    secrets; keys are resolved lazily through a :class:`SecretResolver`.
    """

    @property
    def name(self) -> str:
        """Provider display name (used in results and the audit trail)."""
        ...

    def call(self, messages: list[Message]) -> ProviderResult:
        """Issue a request and return the response, or raise on failure."""
        ...


class EchoProvider:
    """Deterministic no-I/O provider: echoes the last user message.

    Useful as the default, as a test fixture, and as the last-resort fallback
    in a reference pipeline.
    """

    def __init__(self, cost: float = 1.0) -> None:
        self._cost = cost

    @property
    def name(self) -> str:
        return "echo"

    def call(self, messages: list[Message]) -> ProviderResult:
        content = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return ProviderResult(content=content, provider_name=self.name, cost=self._cost)


# A single scripted outcome: an error to raise, a string to echo, or a
# callable mapping messages to a result/error/string.
_Outcome = ProviderError | str | Callable[[list[Message]], object]


class ScriptedProvider:
    """Deterministic scriptable provider for testing retry/fallback.

    ``script`` is a list of outcomes. An outcome is a string (echoed back), an
    exception instance to raise, or a callable that maps the messages to a
    result/error/string (allowing stateful behaviour). When the script is
    exhausted, the last behaviour repeats, so it behaves like a stable provider
    after the prefix.
    """

    def __init__(
        self,
        script: list[_Outcome],
        name: str = "scripted",
        cost: float = 1.0,
    ) -> None:
        self._script = script
        self._name = name
        self._cost = cost
        self._calls = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def calls(self) -> int:
        """Number of times :meth:`call` has been invoked."""
        return self._calls

    def call(self, messages: list[Message]) -> ProviderResult:
        self._calls += 1
        if self._script:
            outcome = self._script[min(self._calls - 1, len(self._script) - 1)]
        else:
            outcome = ""

        if not isinstance(outcome, (str, ProviderError)) and callable(outcome):
            value = outcome(messages)
            if isinstance(value, ProviderResult):
                return value
            if isinstance(value, ProviderError):
                raise value
            return ProviderResult(content=str(value), provider_name=self._name, cost=self._cost)
        if isinstance(outcome, ProviderError):
            raise outcome
        return ProviderResult(content=outcome, provider_name=self._name, cost=self._cost)


class HttpChatProvider:
    """OpenAI-compatible ``/chat/completions`` adapter over stdlib urllib.

    This is the "real provider" path. It is fail-safe: without a configured key
    it raises :class:`ProviderConfig` rather than attempting an unauthenticated
    call. Retryable provider conditions (timeout, HTTP 429/5xx) raise
    :class:`ProviderTransient`; other HTTP statuses raise the appropriate
    gateway error.

    The API key is resolved lazily on each call through a
    :class:`SecretResolver` and is never stored on the instance or logged.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key_env: str = "UM_OPENAI_API_KEY",
        resolver: SecretResolver | None = None,
        timeout_seconds: float = 30.0,
        max_tokens: int = 512,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key_env = api_key_env
        self._resolver = resolver if resolver is not None else env_resolver
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f"http:{self._model}"

    def call(self, messages: list[Message]) -> ProviderResult:
        api_key = self._resolver(self._api_key_env)
        if not api_key:
            raise ProviderConfig(
                f"No API key configured (env var {self._api_key_env!r}) for provider {self._model!r}"
            )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [_serialize_message(m) for m in messages],
            "max_tokens": self._max_tokens,
        }
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status >= 500 or status == 429:
                raise ProviderTransient(f"provider HTTP {status}: {exc.reason}") from exc
            raise self._http_4xx(status, exc.reason) from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise ProviderTransient(f"provider transport failure: {exc}") from exc

        parsed: dict[str, Any]
        try:
            parsed = json.loads(body)
        except ValueError as exc:
            raise ProviderPermanent(f"provider returned malformed JSON: {exc}") from exc
        content = self._extract_content(parsed)
        if content is None:
            raise ProviderPermanent("provider response had no completions content")
        # Rough token-based cost proxy (1 unit per ~2 chars is arbitrary but
        # deterministic); real billing belongs in a provider-specific adapter.
        cost = len(content) / 2.0
        return ProviderResult(content=content, provider_name=self.name, cost=cost)

    @staticmethod
    def _http_4xx(status: int, reason: str) -> ProviderError:
        """Map a 4xx status to a gateway error (auth/config vs permanent)."""
        if status in (401, 403):
            return ProviderConfig(f"provider auth/rejected HTTP {status}: {reason}")
        if status == 400:
            return ProviderPermanent(f"provider rejected request HTTP 400: {reason}")
        return ProviderConfig(f"provider HTTP {status}: {reason}")

    @staticmethod
    def _extract_content(parsed: dict[str, Any]) -> str | None:
        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message")
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        return str(content) if content is not None else None


@dataclass(frozen=True)
class GatewayOutcome:
    """Result of a :meth:`Gateway.generate` call."""

    ok: bool
    content: str | None
    provider_name: str | None
    attempts: int
    cost: float
    last_error: str | None = None


class Gateway:
    """Call a primary provider with retry/backoff, failing over to fallbacks.

    Strategy (deterministic, order-authoritative):
      1. Try the primary provider up to ``retry_policy.max_retries + 1`` times.
         :class:`ProviderTransient` failures back off and retry; every other
         :class:`ProviderPermanent`/:class:`ProviderConfig` fails over at once.
      2. After the primary is exhausted, repeat the same per-provider retry
         budget over each fallback provider, in the order given.
      3. On success return the response; if every provider fails, return a
         failed :class:`GatewayOutcome` carrying the first error seen.
    """

    def __init__(
        self,
        providers: list[Provider],
        *,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Validate provider ordering and keep (optional) retry configuration.

        Args:
            providers: Ordered providers; index 0 is the primary, the rest are
                fallbacks in preference order.
            retry_policy: Backoff policy; ``jitter=False`` + low delays are
                recommended for deterministic tests.
            sleep: Injectable pause between retries (defaults to real sleep).
        """
        if not providers:
            raise ProviderConfig("Gateway requires at least one provider")
        self._providers = list(providers)
        self._policy = retry_policy if retry_policy is not None else RetryPolicy()
        self._sleep = sleep

    @property
    def providers(self) -> list[Provider]:
        """Ordered provider list, primary first."""
        return list(self._providers)

    def generate(self, messages: list[Message], *, max_retries: int | None = None) -> GatewayOutcome:
        """Return a response from the provider chain, or a failure outcome."""
        budget = self._policy.max_retries if max_retries is None else max_retries
        first_error: str | None = None
        total_attempts = 0

        for provider in self._providers:
            attempt = 0
            while attempt <= budget:
                total_attempts += 1
                attempt += 1
                try:
                    result = provider.call(messages)
                except ProviderTransient as exc:
                    if first_error is None:
                        first_error = str(exc)
                    if attempt <= budget:
                        delay = self._policy.get_delay(attempt - 1)
                        if delay > 0:
                            self._sleep(delay)
                        continue
                    break  # retries exhausted -> fail over
                except (ProviderPermanent, ProviderConfig) as exc:
                    if first_error is None:
                        first_error = str(exc)
                    break  # never retry these; fail over
                # Success.
                return GatewayOutcome(
                    ok=True,
                    content=result.content,
                    provider_name=result.provider_name,
                    attempts=total_attempts,
                    cost=result.cost,
                    last_error=None,
                )

        return GatewayOutcome(
            ok=False,
            content=None,
            provider_name=None,
            attempts=total_attempts,
            cost=0.0,
            last_error=first_error or "all providers failed",
        )