"""Tests for the local OpenAI-compatible stub server.

These run a real HTTP loop: start the stub, point an :class:`HttpChatProvider`
at it, and confirm the whole GATEWAY wire path works with no external network
or key. The stub's reply is derived from the request (deterministic), the
response parses through the provider's OpenAI-extractor, and each request is
logged for audit.
"""

from __future__ import annotations

from universal_mind.io import (
    Gateway,
    HttpChatProvider,
    StubChatServer,
)
from universal_mind.io.gateway import Message


def _stub() -> StubChatServer:
    """Start a fresh stub server on an ephemeral port."""
    srv = StubChatServer(log_path=None)
    srv.start()
    return srv


def _provider(srv: StubChatServer, key: str = "local-key") -> HttpChatProvider:
    return HttpChatProvider(srv.base_url, model="stub-1", resolver=lambda _: key)


def test_stub_serves_chat_completions() -> None:
    """A real provider-side request yields a deterministic, derived reply."""
    srv = _stub()
    try:
        provider = _provider(srv)
        result = provider.call([Message(role="user", content="hello world")])
        assert "received 11 chars" in result.content
        assert "hello world" in result.content
    finally:
        srv.stop()


def test_stub_reply_is_deterministic() -> None:
    srv = _stub()
    try:
        provider = _provider(srv)
        a = provider.call([Message(role="user", content="same input")])
        b = provider.call([Message(role="user", content="same input")])
        assert a.content == b.content
    finally:
        srv.stop()


def test_stub_derives_from_last_user_message() -> None:
    srv = _stub()
    try:
        provider = _provider(srv)
        result = provider.call(
            [Message(role="system", content="sys"), Message(role="user", content="the real ask")]
        )
        assert "the real ask" in result.content
        assert "sys" not in result.content.split("received", 1)[1]
    finally:
        srv.stop()


def test_gateway_routes_through_stub() -> None:
    """The composed Gateway honours the stub as a real (primary) provider."""
    srv = _stub()
    try:
        provider = _provider(srv)
        gateway = Gateway([provider])
        outcome = gateway.generate([Message(role="user", content="ping")])
        assert outcome.ok
        assert outcome.provider_name == "http:stub-1"
        assert "ping" in (outcome.content or "")
    finally:
        srv.stop()


def test_stub_logs_requests() -> None:
    srv = _stub()
    try:
        provider = _provider(srv)
        provider.call([Message(role="user", content="log me")])
        records = srv.log.all()
        assert len(records) == 1
        assert records[0]["reply"].startswith("[stub-1]")
        assert records[0]["messages"][0]["content"] == "log me"
    finally:
        srv.stop()


def test_health_endpoint() -> None:
    """A GET to /health returns a JSON status — useful for readiness checks."""
    import json
    import urllib.request

    srv = _stub()
    try:
        with urllib.request.urlopen(f"{srv.base_url}/health", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["status"] == "ok"
        assert body["model"] == "stub-1"
    finally:
        srv.stop()


def test_stub_requires_no_key() -> None:
    """The wire path needs no real credential — locality is the point."""
    srv = _stub()
    try:
        provider = _provider(srv, key="local")
        result = provider.call([Message(role="user", content="no-internet")])
        assert "no-internet" in result.content
    finally:
        srv.stop()