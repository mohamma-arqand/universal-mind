"""Input/output memoization — the type-1 "absorb" (Phase 2a).

The cheapest and most universal form of absorption: remember that "for input X,
the tool produced output Y" and replay it without re-running the tool. This is the
only kind of absorption available for *closed* tools (a licensed app you can reach
but never re-implement), and it accelerates every tool by skipping redundant work.

It is NOT logic-rewrite (that is Phase 2c). It is exact-memoization keyed on a
stable hash of the tool name + deterministic input, so a cache hit is always the
*same* tool with the *same* inputs — never a guess from a vaguely similar request.
A cache miss falls through to the real connector and records the new outcome.

Deterministic and local: a plain in-memory table, keyed by (tool_name, input-key).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from universal_mind.connectors import Connector, ConnectorResult


@dataclass(frozen=True)
class CacheStats:
    """How often the memoizer replayed versus reached a tool."""

    hits: int
    misses: int
    entries: int


def _key(tool_name: str, params: dict[str, Any]) -> str:
    """A stable, order-insensitive content key for a tool invocation."""
    canonical = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{tool_name}\0{canonical}".encode()).hexdigest()
    return f"{tool_name}:{digest[:16]}"


class MemoizingConnector:
    """Wraps any :class:`Connector` and replays cached outcomes for identical
    (tool, input) pairs, so type-1 absorption removes redundant real work.

    Only *successful* results are cached — a failure is never memoized (we do not
    want to replay an error as a result). A cache hit is exact; everything else
    reaches the underlying connector and, on success, is stored for next time.
    """

    def __init__(self, inner: Connector, *, tool_name: str) -> None:
        self._inner = inner
        self._tool_name = tool_name
        self._cache: dict[str, ConnectorResult] = {}
        self._hits = 0
        self._misses = 0

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        key = _key(self._tool_name, params)
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        result = self._inner.connect(spec, params)
        if result.ok:
            self._cache[key] = result
        return result

    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses, entries=len(self._cache))


__all__ = ["CacheStats", "MemoizingConnector", "_key"]