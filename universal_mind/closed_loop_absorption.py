"""Closed-loop absorption — read a spec, re-implement, admit (Phase 2c).

Ties Phase 2b (read the spec) and Phase 2a/2c together into one honest pipeline:

    spec (open/declared)  --read_spec-->  ToolEntry  --absorb_tool-->  internal capability

Only a tool whose spec declares ``absorbable=true`` is re-implemented; the
re-implementation is generated, built in a sandbox, probed against a canonical
input, and ADMITTED only when it reproduces the expected output (the same
``code -> sandbox -> benchmark -> accept/reject`` law the whole project obeys).
A closed tool, or a re-implementation that fails the benchmark, leaves the tool
as a connected (not absorbed) entry — the honest outcome.

Deterministic: the generator maps the declared capability to a tiny safe
vocabulary of pure functions, so a given spec always absorbs the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.absorption import AbsorptionResult, absorb_tool
from universal_mind.spec_introspection import read_spec
from universal_mind.tool_registry import ToolRegistry


@dataclass(frozen=True)
class ClosedLoopResult:
    """The outcome of studying + (optionally) absorbing one open tool spec."""

    tool_name: str
    parsed: bool              # was the spec parseable at all
    error: str                # parse error ("" if parsed)
    absorbed: bool            # was an internal capability admitted
    internal_name: str        # the internal capability's registry name ("" if none)
    notes: tuple[str, ...]    # warnings + absorption reason


def ingest_spec(spec: dict[str, Any], registry: ToolRegistry) -> ClosedLoopResult:
    """Study a tool spec, register the tool, and absorb it if it is open.

    1. ``read_spec`` parses the spec (refusing malformed specs).
    2. The resulting :class:`ToolEntry` is registered in the encyclopedia.
    3. If the tool is absorbable, ``absorb_tool`` re-implements and benchmarks it
       against the canonical probe; an admitted internal capability is also
       registered (under the capability slug).
    4. The result reports every step honestly — a refusal at any stage is a
       concrete outcome, never a silent skip.
    """
    reading = read_spec(spec)
    if reading.entry is None:
        return ClosedLoopResult(
            tool_name=str(spec.get("name", "?")),
            parsed=False,
            error=reading.error,
            absorbed=False,
            internal_name="",
            notes=(),
        )

    entry = reading.entry
    registry.register(entry)

    absorbed_result: AbsorptionResult | None = None
    if entry.absorbable:
        absorbed_result = absorb_tool(entry, registry)

    notes = list(reading.warnings)
    if absorbed_result is not None:
        notes.append(absorbed_result.reason)

    return ClosedLoopResult(
        tool_name=entry.name,
        parsed=True,
        error="",
        absorbed=bool(absorbed_result and absorbed_result.absorbed),
        internal_name=absorbed_result.internal_name if absorbed_result and absorbed_result.absorbed else "",
        notes=tuple(notes),
    )


__all__ = ["ClosedLoopResult", "ingest_spec"]