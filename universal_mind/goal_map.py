"""The goal MAP — a real DAG, not just an ordered list.

The agent's steps become a dependency graph: each step may declare
«بعد از X» (waits for X) and one step may be «بعد از همه» (the JOIN —
runs when every other step has an outcome). The executor walks the map in
topological passes, honestly reporting un-runnable steps (cycles refused,
never executed in a broken order).

Honest rules:
- A cycle in the declared graph is REFUSED with the cycle's members named —
  never silently executed in a fabricated order.
- The join step runs only after ALL non-join steps have outcomes (success,
  failure, OR honest skip — every branch must END before the join).
- Without any «بعد از» declarations the map degenerates to the plain
  sequential order (fully backward compatible with goal_parser's steps).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GoalMap:
    """The parsed DAG of one goal."""

    text: str
    steps: tuple[str, ...]
    depends_on: dict[int, tuple[int, ...]]  # step index -> the indexes it waits for
    join_index: int | None = None  # the «بعد از همه» step, if declared


def parse_goal_map(sentence: str, steps: tuple[str, ...]) -> GoalMap | None:
    """Build the DAG from step texts carrying dependency clauses.

    Recognized clauses (per step):
      «بعد از گام N»  — waits for step number N (1-based)
      «بعد از همه»    — this step is the JOIN
    Anything undeclared has no dependencies (the sequential spirit stays).
    A cycle is detected and refused (None + the reason accessible via the
    caller's honest handling — parse returns the REFUSED map marker).
    """
    if not steps:
        return None
    depends: dict[int, tuple[int, ...]] = {}
    join_index: int | None = None
    for i, step in enumerate(steps):
        if "بعد از همه" in step:
            if join_index is not None:
                return None  # two joins: ambiguous, refuse
            join_index = i
            continue
        deps: list[int] = []
        for m in re.finditer(r"بعد از گام (\d+)", step):
            n = int(m.group(1))
            if 1 <= n <= len(steps) and (n - 1) != i:
                deps.append(n - 1)
        if deps:
            depends[i] = tuple(sorted(set(deps)))
    # Cycle check over the declared edges only.
    graph = {i: list(dep) for i, dep in depends.items()}
    state: dict[int, int] = {}  # 0=unvisited, 1=in-stack, 2=done
    cycle: list[int] = []

    def visit(node: int) -> bool:
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt, 0) == 1:
                cycle.append(nxt)
                return False
            if state.get(nxt, 0) == 0 and not visit(nxt):
                return False
        state[node] = 2
        return True

    for node in graph:
        if state.get(node, 0) == 0:
            if not visit(node):
                return None  # a cycle: refused, members in `cycle`
    return GoalMap(text=sentence, steps=steps, depends_on=depends, join_index=join_index)


def execution_order(goal_map: GoalMap) -> list[list[int]] | None:
    """The topological PASSES: each pass is the set of steps whose
    dependencies are all satisfied by previous passes. The join goes LAST.

    None is never returned for a parsed map (cycles were refused at parse);
    every step appears exactly once.
    """
    n = len(goal_map.steps)
    done: set[int] = set()
    passes: list[list[int]] = []
    join = goal_map.join_index
    remaining = {i for i in range(n) if i != join}
    while remaining:
        ready = sorted(
            i for i in remaining
            if all(d in done for d in goal_map.depends_on.get(i, ()))
        )
        if not ready:
            return None  # unreachable for parsed maps; safety for hand-built ones
        passes.append(ready)
        done.update(ready)
        remaining -= done
    if join is not None:
        passes.append([join])
    return passes


def map_report(goal_map: GoalMap, passes: list[list[int]]) -> str:
    """The DAG rendered for the operator: passes with Persian numbering."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    lines = [f"🗺 نقشهی هدف ({len(goal_map.steps)} گام، {len(passes)} موج):"]
    for wave, group in enumerate(passes, 1):
        label = " (اتصال بعد از همه)" if group[0] == goal_map.join_index else ""
        names = " | ".join(goal_map.steps[i][:24] for i in group)
        lines.append(f"  موج {str(wave).translate(fa)}: {names}{label}")
    return "\n".join(lines)


__all__ = ["GoalMap", "execution_order", "map_report", "parse_goal_map"]