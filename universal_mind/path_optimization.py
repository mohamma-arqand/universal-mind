"""Path optimization — learn which tool (or which order) to prefer, from real runs (Phase 4).

Phase 4a recorded evidence on each tool; Phase 4b now turns that evidence into a
*path* preference. Given a registry whose tools carry an evidence trail (appended
by ``orchestrate`` / ``run_pipeline``), this module distills two standing facts:

1. **per-capability champion** — which tool has the best mean evidence score, so a
   future pipeline picks it without re-discovering it;
2. **an ordered route** — the sequence of capabilities a pipeline should follow,
   ranked by the champions' reliability.

The optimization is *evidence-derived but reversible*: it reads the trail and
returns a preference; applying that preference is a separate, explicit step that
only re-orders (it never deletes a tool or its history).

Deterministic and pure.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.tool_registry import ToolEntry, ToolRegistry


@dataclass(frozen=True)
class Champion:
    """The learned best tool for one capability."""

    capability: str
    tool_name: str
    mean_score: float      # 0.0 when the champion has no evidence yet


@dataclass(frozen=True)
class PathPlan:
    """The learned route: champions ordered by reliability."""

    champions: tuple[Champion, ...]
    route: tuple[str, ...]          # capabilities in descending reliability order


def _mean(entry: ToolEntry) -> float:
    if not entry.evidence:
        return 0.0
    scores = [e["score"] for e in entry.evidence if isinstance(e.get("score"), (int, float))]
    return sum(scores) / len(scores) if scores else 0.0


def learn_path(registry: ToolRegistry) -> PathPlan:
    """Derive one champion per capability and order the route by reliability.

    A capability with no tool is simply absent. A champion with no evidence is
    included (score 0.0) but ranked last — the route prefers proven tools first.
    """
    champions: list[Champion] = []
    for capability in registry.capabilities():
        tools = registry.tools_for(capability)
        if not tools:
            continue
        best = max(tools, key=lambda t: (_mean(t), -len(t.name), t.name))
        champions.append(Champion(capability=capability, tool_name=best.name, mean_score=_mean(best)))

    # Route = capabilities ordered by descending champion reliability.
    ordered = sorted(champions, key=lambda c: (-c.mean_score, c.capability))
    return PathPlan(
        champions=tuple(champions),
        route=tuple(c.capability for c in ordered),
    )


__all__ = ["Champion", "PathPlan", "learn_path"]