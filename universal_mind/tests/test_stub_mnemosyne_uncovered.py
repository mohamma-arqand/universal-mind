"""Coverage for stub_server.py + mnemosyne.py remaining branches."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from universal_mind.core.clock import FrozenClock
from universal_mind.io.stub_server import StubChatServer
from universal_mind.memory.mnemosyne import Mnemosyne, _clamp, _searchable_text
from universal_mind.memory.store import InMemoryStore

# --- StubChatServer ---


def test_base_url_raises_before_start() -> None:
    server = StubChatServer()
    with pytest.raises(RuntimeError):
        _ = server.base_url


def test_stub_unknown_post_path_returns_404() -> None:
    server = StubChatServer()
    url = server.start()
    try:
        req = urllib.request.Request(f"{url}/wrong", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=5)
        assert exc.value.code == 404
    finally:
        server.stop()


def test_stub_unknown_get_path_returns_404() -> None:
    server = StubChatServer()
    url = server.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{url}/nope", timeout=5)
        assert exc.value.code == 404
    finally:
        server.stop()


def test_stub_health_endpoint() -> None:
    server = StubChatServer()
    url = server.start()
    try:
        with urllib.request.urlopen(f"{url}/healthz", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["status"] == "ok"
    finally:
        server.stop()


def test_stub_malformed_json_body() -> None:
    server = StubChatServer()
    url = server.start()
    try:
        req = urllib.request.Request(
            f"{url}/chat/completions", data=b"not-json", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert "choices" in body  # malformed body -> {} -> empty reply, still 200
    finally:
        server.stop()


def test_stub_logs_to_file(tmp_path: Path) -> None:
    log = tmp_path / "requests.jsonl"
    server = StubChatServer(log_path=log)
    url = server.start()
    try:
        req = urllib.request.Request(
            f"{url}/chat/completions", data=json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode(),
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5).read()
    finally:
        server.stop()
    assert log.exists()
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


# --- Mnemosyne ---


def _clock() -> FrozenClock:
    return FrozenClock(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))


def test_searchable_text_non_dict_payload() -> None:
    assert "hello" in _searchable_text({"kind": "note", "payload": "hello world"})


def test_clamp_bounds() -> None:
    assert _clamp(-5.0) == 0.0
    assert _clamp(1.5) == 1.0
    assert _clamp(0.3) == 0.3


def test_recall_filters_by_owner_kind_target() -> None:
    store = InMemoryStore()
    m = Mnemosyne(store, _clock())
    m.record(owner_id="a", kind="fact", payload={}, provenance={})
    m.record(owner_id="b", kind="fact", payload={}, provenance={})
    m.record(owner_id="a", kind="note", payload={}, provenance={})
    m.record(owner_id="a", kind="fact", payload={}, provenance={}, target_record_id="t1")

    assert len(m.recall(owner_id="a", kind="fact")) == 2
    assert len(m.recall(owner_id="zzz")) == 0
    assert len(m.recall(owner_id="a", kind="note")) == 1
    assert len(m.recall(owner_id="a", target_record_id="t1")) == 1


def test_classify_naive_datetime() -> None:
    store = InMemoryStore()
    m = Mnemosyne(store, _clock())
    # record created_at without tzinfo
    store.append({"owner_id": "a", "kind": "x", "created_at": "2024-01-01T12:00:00",
                  "provenance": {}, "payload": {}, "schema_version": 1})
    rec = next(iter(store.read_all()))
    # should not raise; treats naive as UTC
    assert m._classify(rec) is not None


def test_decay_max_age_branch() -> None:
    store = InMemoryStore()
    clock = _clock()
    m = Mnemosyne(store, clock)
    m.record(owner_id="a", kind="fact", payload={}, provenance={})
    # advance clock past max_age
    clock2 = FrozenClock(datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc))
    m2 = Mnemosyne(store, clock2)
    removed = m2.decay(max_age=timedelta(hours=1))
    assert removed == 1