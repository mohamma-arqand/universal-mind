"""Tests for multimodal GATEWAY messages (image/audio parts, backward-compat)."""

from __future__ import annotations

from universal_mind.io import (
    HttpChatProvider,
    Message,
    MessagePart,
    StubChatServer,
)
from universal_mind.io.gateway import _serialize_message


def _stub() -> StubChatServer:
    srv = StubChatServer(log_path=None)
    srv.start()
    return srv


def test_message_part_serialization() -> None:
    """Multimodal parts ride alongside the plain-text content."""
    msg = Message(role="user", content="describe this", parts=(MessagePart(kind="image", data="<img>"),))
    wire = _serialize_message(msg)
    assert wire["content"] == "describe this"
    assert wire["parts"] == [{"kind": "image", "data": "<img>"}]


def test_plain_message_has_no_parts() -> None:
    """A text-only message stays backward-compatible (no parts key)."""
    wire = _serialize_message(Message(role="user", content="hello"))
    assert "parts" not in wire


def test_text_only_default_is_empty_parts() -> None:
    m = Message(role="user", content="hi")
    assert m.parts == ()


def test_stub_serves_image_part() -> None:
    """The stub acknowledges a multimodal part deterministically."""
    srv = _stub()
    try:
        provider = HttpChatProvider(srv.base_url, model="stub-1", resolver=lambda _: "k")
        result = provider.call(
            [Message(role="user", content="look at this", parts=(MessagePart(kind="image", data="<png>"),))]
        )
        assert "parts: image" in result.content
        assert "look at this" in result.content
    finally:
        srv.stop()


def test_stub_handles_multiple_part_kinds() -> None:
    srv = _stub()
    try:
        provider = HttpChatProvider(srv.base_url, model="stub-1", resolver=lambda _: "k")
        result = provider.call(
            [Message(
                role="user",
                content="analyze",
                parts=(MessagePart(kind="image", data="i"), MessagePart(kind="audio", data="a")),
            )]
        )
        assert "parts: audio,image" in result.content
    finally:
        srv.stop()


def test_existing_text_providers_unchanged() -> None:
    """EchoProvider and text-only flows are unaffected by the widening."""
    from universal_mind.io import EchoProvider, Gateway

    gateway = Gateway([EchoProvider()])
    outcome = gateway.generate([Message(role="user", content="ping")])
    assert outcome.ok
    assert outcome.content == "ping"