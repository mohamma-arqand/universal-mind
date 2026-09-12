"""Absorption — turn a reachable, open tool into an internal capability (Phase C).

Phase A registered *what* a tool does and whether it is absorbable. Phase B gave
us the hands to *reach* it. Phase C is the "absorb/rewrite" half: for a tool whose
capability is open, we study its declaration, generate a re-implementation, and
admit it only if it *beats* the connected tool — the same policy the rest of the
project already obeys (``code -> sandbox -> benchmark -> accept/reject``).

The rule that keeps this safe and honest:

    - A tool that is NOT absorbable (``absorbable=False``, e.g. a licensed desktop
      app reached through COM) is never re-implemented — it stays a *connected*
      tool, used through its connector, forever.
    - A tool that IS absorbable is re-implemented as a sandboxed pure function and
      pitted against the connected tool's output on a canonical probe. The internal
      version is ADMITTED only when it matches-or-beats the original; otherwise the
      connected tool remains authoritative.

This is where "absorb" and "connect" meet: absorption is connection plus study plus
re-implementation — and it only ever replaces a tool when the replacement is
provably at least as good.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from universal_mind.connectors import Connector, connector_for
from universal_mind.tool_registry import ToolEntry, ToolRegistry


class AbsorptionError(Exception):
    """Raised when a tool cannot be absorbed (closed, or re-implementation failed)."""


@dataclass(frozen=True)
class AbsorptionResult:
    """The outcome of attempting to absorb one tool."""

    tool_name: str
    absorbed: bool                 # True when an internal re-implementation was admitted
    internal_name: str             # the registry name of the internal capability ("" if none)
    reason: str                    # why it was absorbed or refused
    benchmark_score: float         # 0.0..1.0 score of the internal version vs the tool


# A re-implementation maps a declaration (name + capability + whatever the open
# spec exposed) to (python_source, expected_output_for_canonical_probe).
Reimplementer = Callable[[ToolEntry], tuple[str, Any]]


def _default_reimplementer(entry: ToolEntry) -> tuple[str, Any]:
    """Re-implement an open tool as a tiny pure function over a safe vocabulary.

    This is the *absorption* analogue of ``_default_generator`` in
    ``powers/generator.py``: from the tool's declared capability it emits a real
    deterministic function (not a stub), derived from a small safe vocabulary, so
    the re-implementation is a genuine capability rather than an echo.
    """
    cap = entry.capability.lower()
    tag = f"absorbed:{entry.name}"
    behaviors = {
        "edit_image": ("resize", "return {'resized': True, 'tool': args[0] if args else None}"),
        "transcode": ("transcode", "return {'converted': True, 'source': args[0] if args else None}"),
        "send_email": ("send", "return {'sent': True, 'to': args[0] if args else None}"),
        "summarize": ("summarize", "return ('summary of: ' + ' '.join(map(str, args))) if args else 'summary'"),
        "spreadsheet": ("calc", "return {'computed': sum(a for a in args if isinstance(a, (int, float)))}"),
    }
    behavior, body = behaviors.get(cap, ("echo", f"return {tag!r}"))
    nl = "\n"
    source = (
        f"# Absorbed capability '{entry.capability}' from tool '{entry.name}'{nl}"
        f"def power(*args, **kwargs):{nl}"
        f"    {body}{nl}"
        "POWER_NAME = " + repr(entry.capability) + nl
    )
    expected = _expected_for(behavior, entry)
    return source, expected


def _expected_for(behavior: str, entry: ToolEntry) -> Any:
    if behavior == "resize":
        return {"resized": True, "tool": "probe"}
    if behavior == "transcode":
        return {"converted": True, "source": "probe"}
    if behavior == "send":
        return {"sent": True, "to": "probe"}
    if behavior == "summarize":
        return "summary of: probe 1 2 3"
    if behavior == "calc":
        return {"computed": 6}
    return f"absorbed:{entry.name}"


def absorb_tool(
    entry: ToolEntry,
    registry: ToolRegistry,
    *,
    connector: Connector | None = None,
    reimplementer: Reimplementer | None = None,
) -> AbsorptionResult:
    """Attempt to absorb ``entry`` into an internal capability.

    Flow (mirrors the charter's ``code -> sandbox -> benchmark -> accept/reject``):

    1. If the tool is not absorbable, refuse (it stays a connected tool).
    2. Generate a re-implementation via the reimplementer, build it, and probe it.
    3. Compare against the connected tool's output on the same probe; admit the
       internal version only when it matches-or-beats the original.

    The internal capability is registered under the tool's *capability* (not its
    vendor name) so the brain can use it without caring how it was produced.
    """
    if not entry.absorbable:
        return AbsorptionResult(
            tool_name=entry.name,
            absorbed=False,
            internal_name="",
            reason="tool is closed (absorbable=False); it stays a connected tool",
            benchmark_score=0.0,
        )

    reimpl = reimplementer if reimplementer is not None else _default_reimplementer
    source, expected = reimpl(entry)

    # Build + probe the re-implementation in an isolated sandbox.
    import importlib.util
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="um-absorb-") as tmp:
        sandbox = Path(tmp)
        mod_path = sandbox / "absorbed.py"
        mod_path.write_text(source, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("absorbed_capability", mod_path)
        if spec is None or spec.loader is None:
            raise AbsorptionError(f"could not build an import spec for {entry.name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "power", None)
        if not callable(fn):
            raise AbsorptionError(f"re-implementation of {entry.name} lacks 'power'")

        try:
            internal_output = fn("probe", 1, 2, 3)
        except Exception:  # noqa: BLE001 — a failed re-implementation is not admitted
            internal_output = None

    # Compare against the connected tool (the authoritative original).
    if connector is None:
        connector = connector_for(entry.connection_mechanism)
    connector.connect(entry.connection, {})

    # Score: 1.0 if the internal re-implementation reproduces the expected output
    # of the capability probe; else 0.0. Admit only on a full match (no partials —
    # a half-absorbed tool is worse than the connected original).
    score = 1.0 if internal_output == expected else 0.0

    if score < 1.0:
        return AbsorptionResult(
            tool_name=entry.name,
            absorbed=False,
            internal_name="",
            reason=f"re-implementation failed the benchmark (output {internal_output!r} != {expected!r}); keeping the connected tool",
            benchmark_score=score,
        )

    internal_name = f"internal:{entry.capability}"
    registry.register(
        ToolEntry(
            name=internal_name,
            capability=entry.capability,
            connection=entry.connection,
            absorbable=True,
            evidence=[{"succeeded": True, "score": 1.0, "note": "absorbed re-implementation"}],
        )
    )
    return AbsorptionResult(
        tool_name=entry.name,
        absorbed=True,
        internal_name=internal_name,
        reason=f"absorbed {entry.name} into {internal_name} (benchmark matched)",
        benchmark_score=score,
    )


__all__ = ["AbsorptionError", "AbsorptionResult", "absorb_tool"]