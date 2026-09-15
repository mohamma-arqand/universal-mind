"""Orchestrated synthesis — many tools, one artifact (super-platform Phase D).

Phases A–C made tools reachable and absorbable. Phase D is where "more than the
sum of its parts" becomes concrete: given a high-level request that names several
needed capabilities, the brain reaches each, collects their evidence-anchored
outputs, and *fuses* them into a single new artifact D that no single tool produced
alone — the same "synthesis, not integration" axiom the project already holds, now
generalized from two pre-selected specialists to any N tools in the encyclopedia.

Deterministic and local: it reads the registry, reaches tools through their
connectors, and fuses through an injectable composer (defaulting to a structured
join). Nothing here invents an output; a capability with no tool simply fails that
sub-request rather than fabricating a result.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from universal_mind.connectors import Connector, connector_for
from universal_mind.tool_registry import ToolEntry, ToolRegistry


def _perf() -> float:
    """A monotonic clock with a fixed unit (seconds)."""
    return time.perf_counter()

# Resolve the connector for a tool. Defaults to the built-in mechanism mapping,
# but a caller may inject a factory (e.g. to route a capability to a custom
# connector such as MediaToolConnector).
ConnectorFactory = Callable[[ToolEntry], Connector]


def _default_connector(tool: ToolEntry) -> Connector:
    return connector_for(tool.connection_mechanism)


class OrchestrationError(Exception):
    """Raised when a requested capability cannot be honored by any tool."""


@dataclass(frozen=True)
class SubOutput:
    """One tool's contribution to the synthesis."""

    capability: str
    tool_name: str
    output: Any
    ok: bool
    error: str = ""
    duration_ms: float = 0.0   # real wall-clock time the tool took (measured)


@dataclass(frozen=True)
class Synthesis:
    """The fused artifact D plus its provenance."""

    output: Any
    sub_outputs: tuple[SubOutput, ...]
    ok: bool                  # True only when every requested capability succeeded


# A composer fuses a list of per-capability results into one artifact D.
Composer = Callable[[list[SubOutput]], Any]


def _default_composer(sub_outputs: list[SubOutput]) -> Any:
    """Default fusion: a structured bundle keyed by capability (never a lossy concat)."""
    return {
        "synthesized_from": {s.capability: s.output for s in sub_outputs if s.ok},
    }


def orchestrate(
    registry: ToolRegistry,
    capabilities: list[str],
    *,
    composer: Composer | None = None,
    connector_factory: ConnectorFactory | None = None,
    capability_params: dict[str, dict[str, Any]] | None = None,
) -> Synthesis:
    """Reach a tool for each needed capability and fuse their outputs into one D.

    ``capabilities`` is the list of WHAT the request needs (in order); for each,
    the registry's best tool (highest evidence) is reached through its connector.
    If any capability has no tool, that sub-output is ``ok=False`` and the whole
    synthesis is ``ok=False`` — a missing capability is never papered over.

    The ``composer`` fuses the sub-outputs; the default produces a structured
    bundle so D carries exactly which tool satisfied which capability (auditable).
    ``connector_factory`` overrides the mechanism-derived connector (e.g. to route
    a capability to a custom connector such as ``MediaToolConnector``).
    ``capability_params`` feeds each capability the parameters the caller (or the
    Persian router) specified: {"data": {"operation": "stats", "data": [2, 4]}} —
    so «میانگین ۲ و ۴» computes [2, 4], not a default series.
    """
    fuse = composer if composer is not None else _default_composer
    factory = connector_factory if connector_factory is not None else _default_connector
    sub_outputs: list[SubOutput] = []
    for capability in capabilities:
        tool = registry.best_for(capability)
        call_params = (capability_params or {}).get(capability, {})
        if tool is None:
            sub_outputs.append(
                SubOutput(capability=capability, tool_name="", output=None, ok=False,
                          error=f"no tool can honor '{capability}'")
            )
            continue
        start = _perf()
        result = factory(tool).connect(tool.connection, call_params)
        duration_ms = (_perf() - start) * 1000.0
        sub_outputs.append(
            SubOutput(
                capability=capability,
                tool_name=tool.name,
                output=result.output,
                ok=result.ok,
                error=result.error,
                duration_ms=round(duration_ms, 4),
            )
        )
        # Record the outcome on the tool's evidence trail so the next synthesis
        # ranks tools by what actually worked (feeds Phase E).
        tool.evidence.append({"succeeded": result.ok, "score": 1.0 if result.ok else 0.0, "note": capability})

    fused = fuse(sub_outputs)
    all_ok = all(s.ok for s in sub_outputs)
    return Synthesis(output=fused, sub_outputs=tuple(sub_outputs), ok=all_ok)


__all__ = ["ConnectorFactory", "OrchestrationError", "SubOutput", "Synthesis", "orchestrate"]