"""Execution budgeting — allocate a finite resource across specialists by merit.

The charter's picture is a *manager*, not a chatbot: lots of capable
specialists, each good at one thing, and a central mind that divides work and
spends a finite budget wisely. This module is that scarcity model: given a set
of registered organs (each with cost + credibility) and a total budget, it
selects the subset that maximizes credibility per unit cost while staying under
budget — a deterministic knapsack/greedy selection, so the result is
explainable ("why did we drop X?") rather than an opaque optimizer.

Pure and local: it reads descriptors, never executes anything.
"""

from __future__ import annotations

from dataclasses import dataclass

from universal_mind.pantheon.registry import OrganDescriptor


@dataclass(frozen=True)
class BudgetAllocation:
    """The outcome of a budgeting pass: who runs, who is dropped, and why."""

    selected: tuple[str, ...]          # organ names that fit within budget
    total_cost: float                  # cost of the selected set
    remaining: float                   # budget left over
    dropped: tuple[str, ...]           # organs excluded (over budget / no merit)
    ranking: tuple[str, ...]           # selected organs in value order (best first)


def _value(organ: OrganDescriptor) -> float:
    """Merit per unit cost — higher is better (credibility weighted by latency)."""
    # Credibility is the primary trust; a slow organ is penalized lightly so a
    # cheap, credible specialist beats a costly one of equal trust.
    if organ.cost <= 0:
        return organ.credibility
    return organ.credibility / organ.cost


def allocate_budget(
    organs: list[OrganDescriptor],
    budget: float,
    *,
    min_credibility: float = 0.0,
) -> BudgetAllocation:
    """Select the best subset of ``organs`` within ``budget``.

    Greedy by merit-per-cost (a standard, deterministic approximation of the
    0/1 knapsack). Organs below ``min_credibility`` are never admitted. When the
    budget is too small for the next-best organ, it (and lower-value organs) are
    dropped with an explanation. Deterministic: ties resolve by name.
    """
    eligible = sorted(
        (o for o in organs if o.credibility >= min_credibility),
        key=lambda o: (-_value(o), o.name),
    )

    selected: list[OrganDescriptor] = []
    total = 0.0
    dropped: list[OrganDescriptor] = []
    for organ in eligible:
        if total + organ.cost <= budget:
            selected.append(organ)
            total += organ.cost
        else:
            dropped.append(organ)

    # Organs that were below the credibility floor never even entered the sort.
    below_floor = [o for o in organs if o.credibility < min_credibility]
    dropped_all = dropped + below_floor

    return BudgetAllocation(
        selected=tuple(o.name for o in selected),
        total_cost=round(total, 4),
        remaining=round(budget - total, 4),
        dropped=tuple(o.name for o in dropped_all),
        ranking=tuple(o.name for o in selected),
    )


def explain(allocation: BudgetAllocation, organs: dict[str, OrganDescriptor]) -> str:
    """A one-line, human-readable explanation of the allocation decision."""
    if not allocation.selected:
        return "nothing affordable within the budget"
    head = ", ".join(allocation.selected)
    if allocation.dropped:
        return f"selected {head} (cost {allocation.total_cost}); dropped {', '.join(allocation.dropped)}"
    return f"selected {head} (cost {allocation.total_cost}); nothing dropped"