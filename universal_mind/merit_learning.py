"""Self-evolution over tools — learn which tools deserve which work (Phase E).

Phases A–D made tools reachable, absorbable, and fusable. Phase E closes the loop
with *merit learning*: after the brain has actually run tools and recorded evidence
(Phase D appends one outcome per run), this layer distills that trail into a
*standing preference* — which tool best honors each capability — and keeps the
registry's ranking honest.

This is the tool-analogue of the project's Prometheus self-evolution: it observes
past outcomes and proposes a better selection, but it NEVER mutates a tool or
fabricates evidence. The only output is a recommendation plus the re-ranked view;
applying a recommendation is an explicit, reversible registry re-order.

Deterministic and pure: reads evidence, emits a recommendation, records nothing
unless asked via :func:`apply_recommendation` (a reversible registry-level change).
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.tool_registry import ToolEntry, ToolRegistry


@dataclass(frozen=True)
class MeritRecommendation:
    """A learned preference: for a capability, who should be promoted/demoted."""

    capability: str
    action: str            # "promote" | "demote" | "noop"
    tool_name: str
    reason: str


@dataclass(frozen=True)
class MeritReport:
    """The full learned view across capabilities."""

    recommendations: tuple[MeritRecommendation, ...]
    summary: str


def learn_merits(registry: ToolRegistry) -> MeritReport:
    """Derive, not apply, a standing preference from each tool's evidence trail.

    For each capability known to the registry, classify each tool by its evidence:
    - "promote": a reliable tool (mean success >= 0.5) worth keeping/raising;
    - "demote": a tool that failed every recorded run;
    - "noop": no evidence yet, so the ranking is left untouched (no guessing).

    The report is a pure recommendation — applying it is a separate, reversible step.
    """
    recommendations: list[MeritRecommendation] = []
    # Collect the distinct capabilities the registry knows about.
    capabilities = registry.capabilities()

    for capability in sorted(capabilities):
        tools = registry.tools_for(capability)
        for tool in tools:
            score = _mean_score(tool)
            if not tool.evidence:
                recommendations.append(
                    MeritRecommendation(capability, "noop", tool.name,
                                        "no evidence yet — leaving ranking unchanged")
                )
            elif score == 0.0:
                recommendations.append(
                    MeritRecommendation(capability, "demote", tool.name,
                                        "every recorded run failed")
                )
            elif score >= 0.5:
                recommendations.append(
                    MeritRecommendation(capability, "promote", tool.name,
                                        f"reliable at {score:.2f} mean success over {len(tool.evidence)} run(s)")
                )
    if not recommendations:
        summary = "no capabilities have enough evidence to learn from"
    else:
        summary = (
            f"{len(recommendations)} meriting recommendation(s) "
            f"across {len(capabilities)} capability(ies)"
        )
    return MeritReport(recommendations=tuple(recommendations), summary=summary)


def apply_recommendation(registry: ToolRegistry, rec: MeritRecommendation) -> None:
    """Realize a recommendation by re-ordering the tool's evidence (reversible).

    A "demote" re-marks the tool's evidence as failed so the registry's ranking
    drops it; a "promote" records a success point so it rises. This is a
    registry-level, reversible change — it never deletes a tool or its history.
    """
    # Find the tool by name.
    tool: ToolEntry | None = None
    for t in registry.tools_for(rec.capability):
        if t.name == rec.tool_name:
            tool = t
            break
    if tool is None:
        return
    if rec.action == "demote":
        tool.evidence.append({"succeeded": False, "score": 0.0, "note": "merit-demote"})
    elif rec.action == "promote":
        tool.evidence.append({"succeeded": True, "score": 1.0, "note": "merit-promote"})


def _mean_score(entry: ToolEntry) -> float:
    """Mean success score over the evidence trail; 0.0 with no trail."""
    if not entry.evidence:
        return 0.0
    scores = [e["score"] for e in entry.evidence if isinstance(e.get("score"), (int, float))]
    return sum(scores) / len(scores) if scores else 0.0


__all__ = ["MeritRecommendation", "MeritReport", "apply_recommendation", "learn_merits"]