"""Tests for input/output memoization (super-platform Phase 2a)."""

from __future__ import annotations

from universal_mind.connectors import ConnectorResult
from universal_mind.memoization import MemoizingConnector


class _CountingConnector:
    """A fake connector that counts how many times it actually ran."""

    def __init__(self) -> None:
        self.calls = 0

    def connect(self, spec: object, params: dict[str, object]) -> ConnectorResult:
        self.calls += 1
        return ConnectorResult(ok=True, output=f"result-{self.calls}")


def test_memoizer_replays_identical_input() -> None:
    inner = _CountingConnector()
    mem = MemoizingConnector(inner, tool_name="t")
    a = mem.connect({}, {"x": 1})
    b = mem.connect({}, {"x": 1})  # identical input -> cache hit
    assert a.output == b.output == "result-1"
    assert inner.calls == 1  # the tool ran only once
    stats = mem.stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.entries == 1


def test_different_input_reaches_tool() -> None:
    inner = _CountingConnector()
    mem = MemoizingConnector(inner, tool_name="t")
    mem.connect({}, {"x": 1})
    mem.connect({}, {"x": 2})
    assert inner.calls == 2
    assert mem.stats().entries == 2


def test_failure_is_not_cached() -> None:
    class _Failing:
        def __init__(self) -> None:
            self.calls = 0

        def connect(self, spec: object, params: dict[str, object]) -> ConnectorResult:
            self.calls += 1
            return ConnectorResult(ok=False, output=None, error="boom")

    inner = _Failing()
    mem = MemoizingConnector(inner, tool_name="t")
    mem.connect({}, {"x": 1})
    mem.connect({}, {"x": 1})  # failure not cached -> re-runs
    assert inner.calls == 2
    assert mem.stats().entries == 0


def test_key_is_order_insensitive() -> None:
    inner = _CountingConnector()
    mem = MemoizingConnector(inner, tool_name="t")
    a = mem.connect({}, {"a": 1, "b": 2})
    b = mem.connect({}, {"b": 2, "a": 1})  # same content, different order -> hit
    assert a.output == b.output
    assert inner.calls == 1