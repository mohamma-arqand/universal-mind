"""Tests for shared knowledge (super-platform Phase 5a)."""

from __future__ import annotations

from universal_mind.shared_knowledge import SharedKnowledge


def test_publish_and_read_roundtrip() -> None:
    sk = SharedKnowledge()
    sk.publish("recipient_email", "a@b.c", produced_by="gmail")
    assert sk.read("recipient_email") == "a@b.c"
    assert sk.known("recipient_email") is True


def test_read_missing_returns_default() -> None:
    sk = SharedKnowledge()
    assert sk.read("unknown") is None
    assert sk.read("unknown", default="fallback") == "fallback"


def test_overwrite_updates_producer() -> None:
    sk = SharedKnowledge()
    sk.publish("k", 1, produced_by="a")
    sk.publish("k", 2, produced_by="b")
    assert sk.read("k") == 2
    fact = sk.latest()[0]
    assert fact.produced_by == "b"


def test_latest_reports_provenance() -> None:
    sk = SharedKnowledge()
    sk.publish("x", 1, produced_by="tool-a")
    facts = sk.latest()
    assert len(facts) == 1
    assert facts[0].produced_by == "tool-a"


def test_cross_tool_sharing() -> None:
    # Tool A publishes; tool B (a different name) reads the same fact.
    sk = SharedKnowledge()
    sk.publish("api_key_name", "UM_OPENAI_API_KEY", produced_by="tool-secret")
    # A different tool reads it back.
    assert sk.read("api_key_name") == "UM_OPENAI_API_KEY"