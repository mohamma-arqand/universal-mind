"""Tests for the GATEWAY layer: providers, retry/backoff, and failover."""

from __future__ import annotations

import pytest

from universal_mind.core.errors import RetryPolicy
from universal_mind.io import (
    EchoProvider,
    Gateway,
    GatewayOutcome,
    HttpChatProvider,
    Message,
    Provider,
    ScriptedProvider,
)
from universal_mind.io.errors import (
    ProviderConfig,
    ProviderPermanent,
    ProviderTransient,
)


def msgs(content: str = "hi") -> list[Message]:
    """Build a single user message."""
    return [Message(role="user", content=content)]


def no_delay_policy(max_retries: int = 2) -> RetryPolicy:
    """A deterministic zero-delay retry policy for tests."""
    return RetryPolicy(max_retries=max_retries, base_delay_seconds=0.0, jitter=False)


def test_echo_provider_returns_last_user_message() -> None:
    """EchoProvider returns the most recent user message."""
    provider = EchoProvider()
    result = provider.call([Message(role="system", content="be nice"), Message(role="user", content="hello")])
    assert result.content == "hello"
    assert result.provider_name == "echo"
    assert isinstance(provider, Provider)


def test_scripted_provider_echoes_script() -> None:
    """ScriptedProvider yields script values in order."""
    provider = ScriptedProvider(["one", "two"])
    assert provider.call(msgs()).content == "one"
    assert provider.call(msgs()).content == "two"
    # Last behaviour repeats once the script is exhausted.
    assert provider.call(msgs()).content == "two"
    assert provider.calls == 3


def test_scripted_provider_raises_scripted_error() -> None:
    """A scripted ProviderTransient propagates from call()."""
    provider = ScriptedProvider([ProviderTransient("flaky")])
    with pytest.raises(ProviderTransient):
        provider.call(msgs())


def test_scripted_provider_callable_outcome() -> None:
    """A callable outcome can inspect the messages and return a result."""
    provider = ScriptedProvider([lambda ms: ms[0].content.upper()])
    result = provider.call(msgs("ping"))
    assert result.content == "PING"


def test_gateway_primary_success() -> None:
    """A healthy primary provider answers on the first attempt."""
    outcome = Gateway([EchoProvider()]).generate(msgs("hey"))
    assert outcome.ok
    assert outcome.content == "hey"
    assert outcome.provider_name == "echo"
    assert outcome.attempts == 1


def test_gateway_retries_transient_then_succeeds() -> None:
    """Transient failures back off and recover within the budget."""
    provider = ScriptedProvider([ProviderTransient("1"), ProviderTransient("2"), "ok"])
    gateway = Gateway([provider], retry_policy=no_delay_policy(max_retries=2))
    outcome = gateway.generate(msgs())
    assert outcome.ok
    assert outcome.content == "ok"
    assert outcome.provider_name == "scripted"
    assert outcome.attempts == 3
    assert provider.calls == 3


def test_gateway_records_backoff_delays() -> None:
    """Backoff delays are applied (and injectable) between retries."""
    delays: list[float] = []

    def sleep(delay: float) -> None:
        delays.append(delay)

    scripted = ScriptedProvider([ProviderTransient("1"), ProviderTransient("2"), "ok"])
    policy = RetryPolicy(max_retries=2, base_delay_seconds=1.0, jitter=False)
    gateway = Gateway([scripted], retry_policy=policy, sleep=sleep)
    outcome = gateway.generate(msgs())
    assert outcome.ok
    assert delays == [1.0, 2.0]
    assert outcome.attempts == 3


def test_gateway_fails_over_to_fallback() -> None:
    """A permanently failing primary fails over to the next provider."""
    primary = ScriptedProvider([ProviderPermanent("model collapsed")])
    gateway = Gateway([primary, EchoProvider()], retry_policy=no_delay_policy())
    outcome = gateway.generate(msgs("fallback"))
    assert outcome.ok
    # Fail-over happened immediately (permanent), so primary had 1 attempt.
    assert outcome.provider_name == "echo"
    assert outcome.content == "fallback"
    assert outcome.attempts == 2


def test_gateway_transient_exhaustion_fails_over() -> None:
    """Retries exhausted on the primary then fail over to the fallback."""
    primary = ScriptedProvider([ProviderTransient("always down")])
    gateway = Gateway([primary, EchoProvider()], retry_policy=no_delay_policy(max_retries=2))
    outcome = gateway.generate(msgs("retry-then-fall"))
    assert outcome.ok
    assert outcome.provider_name == "echo"
    # 3 attempts on primary + 1 on echo.
    assert outcome.attempts == 4
    assert primary.calls == 3


def test_gateway_all_providers_fail() -> None:
    """When every provider fails, a failed outcome reports the first error."""
    gateway = Gateway(
        [ScriptedProvider([ProviderPermanent("p1 dead")]), ScriptedProvider([ProviderTransient("p2 dead")], name="p2")],
        retry_policy=no_delay_policy(max_retries=1),
    )
    outcome = gateway.generate(msgs())
    assert not outcome.ok
    assert outcome.content is None
    assert outcome.provider_name is None
    assert outcome.last_error is not None
    assert "p1 dead" in (outcome.last_error or "")


def test_gateway_requires_at_least_one_provider() -> None:
    """An empty provider list is a configuration error."""
    with pytest.raises(ProviderConfig):
        Gateway([])


def test_gateway_deterministic() -> None:
    """Identical calls yield identical attempts/cost/provider."""
    first = Gateway([EchoProvider(cost=2.5)]).generate(msgs("x"))
    second = Gateway([EchoProvider(cost=2.5)]).generate(msgs("x"))
    assert (first.attempts, first.cost, first.provider_name) == (
        second.attempts, second.cost, second.provider_name,
    )
    assert first.cost == 2.5


def test_cost_propagates_from_provider_result() -> None:
    """The provider-reported cost flows into the outcome."""
    outcome = Gateway([EchoProvider(cost=7.0)]).generate(msgs())
    assert outcome.cost == 7.0


def test_gateway_accepts_provider_instances() -> None:
    """ScriptedProvider is duck-typed as a Provider (runtime protocol)."""
    assert isinstance(ScriptedProvider(["x"]), Provider)


def test_http_provider_requires_key() -> None:
    """Without a configured key, HttpChatProvider is fail-safe (ProviderConfig)."""
    provider = HttpChatProvider(
        "https://example.test/v1", "demo",
        resolver=lambda _name: None,
    )
    with pytest.raises(ProviderConfig):
        provider.call(msgs())


def test_http_provider_http_4xx_mapping() -> None:
    """HTTP status classification: 401/403 are config; 400 is permanent."""
    assert isinstance(HttpChatProvider._http_4xx(401, "unauthorized"), ProviderConfig)
    assert isinstance(HttpChatProvider._http_4xx(403, "forbidden"), ProviderConfig)
    assert isinstance(HttpChatProvider._http_4xx(400, "bad request"), ProviderPermanent)
    assert isinstance(HttpChatProvider._http_4xx(404, "missing"), ProviderConfig)


def test_http_provider_extract_content() -> None:
    """content is pulled from the first completion message."""
    payload = {"choices": [{"message": {"role": "assistant", "content": "answer"}}]}
    assert HttpChatProvider._extract_content(payload) == "answer"
    assert HttpChatProvider._extract_content({"choices": []}) is None
    assert HttpChatProvider._extract_content({}) is None


def test_http_provider_is_a_provider() -> None:
    """HttpChatProvider conforms to the Provider protocol surface."""
    provider = HttpChatProvider("https://x/v1", "m", resolver=lambda _n: None)
    assert isinstance(provider, Provider)
    assert "m" in provider.name


def test_gateway_outcome_shape() -> None:
    """GatewayOutcome carries the full audit shape."""
    outcome: GatewayOutcome = Gateway([EchoProvider()]).generate(msgs("shape"))
    assert outcome.content == "shape"
    assert outcome.cost >= 0
    assert isinstance(outcome.attempts, int)