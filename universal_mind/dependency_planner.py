"""The dependency planner — a chain that RESPECTS what each operation needs.

The router maps words to capabilities; the planner goes further: it understands
WHAT each consuming operation requires (an image to embed, a table to render,
a series to plot) and reorders/chooses accordingly:

1. TOPOLOGY: consumers run after their producers, even when the operator said
   them in the opposite order («گزارش بساز و نمودارش کن») — the plan is derived
   from the operations' real needs, not the sentence's word order.
2. OPERATION SELECTION: when a consuming capability fires but the sentence gave
   it no explicit operation, the planner picks the operation that USES what the
   chain already produces (pdf → persian_report when a chart is in the chain),
   so the synthesis is real, not a disconnected pair of artifacts.
3. HONESTY: the planner only reorders within the operator's chosen capability
   set — it never invents a capability, never drops one, and never overrides an
   explicitly requested operation.

Deterministic and pure: same inputs → same plan, always.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# The needs table — what each consuming operation REQUIRES to be worth running.
# producers: capabilities that (can) produce that resource.
# ---------------------------------------------------------------------------

_IMAGE_PRODUCERS: tuple[str, ...] = ("chart", "media", "image", "vision")
_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

# Which capabilities produce which resource. The planner reorders a CONSUMER
# of a resource after its PRODUCER — nothing else moves.
_SERIES_PRODUCERS: tuple[str, ...] = ("data", "ai", "compute")  # numbers/tables
_PLOT_CONSUMERS: tuple[str, ...] = ("chart",)  # need a series
_IMAGE_CONSUMERS: tuple[str, ...] = ("pdf", "image")  # need an image
_STATS_CONSUMERS: tuple[str, ...] = ("pdf",)  # a report can tabulate real numbers
_SINK_CONSUMERS: tuple[str, ...] = ("notify", "archive", "database")  # run last, consume anything

# pdf consumes BOTH image and stats: it must wait for whichever producer is in
# the chain (chart for the image flow, data for the stats-table flow).


# Which operation a capability should run when the sentence gave none AND the
# chain provides the resource it needs (the synthesis-aware default).
_NEEDS_BASED_OPERATION: dict[tuple[str, str], str] = {
    # capability, resource-available → the operation that consumes that resource
    ("pdf", "image"): "persian_report",
    ("image", "image"): "watermark",  # an image in the chain → watermark it in
}


@dataclass(frozen=True)
class PlannedStep:
    """One step of the plan: the capability, its chosen operation, and why."""

    capability: str
    operation: str | None  # None = the suite's own default
    reason: str  # human-readable Persian explanation of the choice


@dataclass(frozen=True)
class ExecutionPlan:
    """A dependency-respecting, synthesis-aware chain plan."""

    steps: tuple[PlannedStep, ...]
    reorder_happened: bool  # the topology moved a consumer after its producer
    notes: tuple[str, ...] = field(default_factory=tuple)


def _capability_order(caps: list[str]) -> list[str]:
    """Topological sort over the needs table (stable, cycle-free by design).

    Rules: series producers (data/ai/compute) precede plot consumers (chart);
    image producers (chart/media/image/vision) precede image consumers (pdf).
    Everything else keeps its routed order — the planner moves a capability
    ONLY when a real dependency demands it.
    """
    remaining = list(caps)
    ordered: list[str] = []
    while remaining:
        progressed = False
        for cap in list(remaining):
            blockers: list[str] = []
            if cap in _PLOT_CONSUMERS:
                blockers = [p for p in _SERIES_PRODUCERS if p in remaining]
            elif cap in _STATS_CONSUMERS:
                # pdf/tabulate consumers wait on BOTH the stats producers and
                # the image producers (either flow can feed the report).
                blockers = [
                    p
                    for p in (*_SERIES_PRODUCERS, *_IMAGE_PRODUCERS)
                    if p in remaining
                ]
            elif cap in _SINK_CONSUMERS:
                blockers = [p for p in remaining if p != cap]
            elif cap in _IMAGE_CONSUMERS:
                blockers = [p for p in _IMAGE_PRODUCERS if p in remaining]
            if not blockers:
                ordered.append(cap)
                remaining.remove(cap)
                progressed = True
        if not progressed:
            # A cycle the table cannot express: keep the routed order (honest).
            ordered.extend(remaining)
            break
    return ordered


def plan_chain(
    caps: list[str],
    capability_params: dict[str, dict[str, Any]] | None = None,
) -> ExecutionPlan:
    """Turn the routed capability list into a dependency-respecting plan.

    ``caps`` is the routed chain (from the vocabulary). ``capability_params``
    is the params extracted from the sentence; an explicitly extracted
    ``operation`` is ALWAYS kept — the planner only chooses when the sentence
    was silent.
    """
    params = capability_params or {}
    planned = _capability_order(list(caps))
    reorder = planned != caps

    steps: list[PlannedStep] = []
    notes: list[str] = []
    produced_images = any(c in _IMAGE_PRODUCERS for c in planned)

    for cap in planned:
        given = params.get(cap) or {}
        explicit_op = given.get("operation")
        if explicit_op:
            steps.append(PlannedStep(capability=cap, operation=str(explicit_op), reason="عملیات صریح از فرمان"))
            continue
        # Synthesis-aware default: use the resource the chain produces.
        resource = "image" if cap in ("pdf", "image") and produced_images else None
        chosen = _NEEDS_BASED_OPERATION.get((cap, resource)) if resource else None
        if chosen:
            steps.append(PlannedStep(
                capability=cap, operation=chosen,
                reason=f"عملیات {chosen} چون زنجیره تصویر تولید میکند (سنتز واقعی)",
            ))
            notes.append(f"{cap}: {chosen} — سنتز با خروجی زنجیره")
        else:
            steps.append(PlannedStep(capability=cap, operation=None, reason="عملیات پیشفرض سوئیت"))
    if reorder:
        notes.append("ترتیب اصلاح شد: تولیدکنندهها قبل از مصرفکنندهها")
    return ExecutionPlan(
        steps=tuple(steps), reorder_happened=reorder, notes=tuple(notes)
    )


def plan_params(plan: ExecutionPlan) -> dict[str, dict[str, Any]]:
    """The capability_params the orchestrator should use for this plan.

    Each step's chosen operation is materialized into the params dict (the
    planner's selection is what runs); explicit sentence params pass through.
    """
    out: dict[str, dict[str, Any]] = {}
    for step in plan.steps:
        entry: dict[str, Any] = {}
        if step.operation is not None:
            entry["operation"] = step.operation
        if entry:
            out[step.capability] = entry
    return out


__all__ = ["ExecutionPlan", "PlannedStep", "plan_chain", "plan_params"]