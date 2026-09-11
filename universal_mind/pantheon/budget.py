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


def select_organs_for_domains(
    organs: list[OrganDescriptor],
    domains: list[str],
    budget: float,
    *,
    min_credibility: float = 0.0,
) -> tuple[dict[str, str], BudgetAllocation]:
    """Pick one organ per needed domain under a shared budget.

    For each needed domain, gather the organs that can honor it (exact domain
    match first, then substring over purpose/signature, falling back to all).
    Then run a single :func:`allocate_budget` over that candidate pool so a
    finite budget — not merely credibility — decides which specialist each
    domain gets. Returns a ``domain -> organ name`` mapping plus the allocation
    that produced it. Domains that stay unaffordable are simply absent.

    This is the bridge between the budgeting model and a real resolution pass:
    the same deterministic merit-per-cost rule picks the specialists.
    """
    per_domain: list[OrganDescriptor] = []
    chosen: dict[str, str] = {}
    for domain in domains:
        candidates = _candidates_for(organs, domain)
        # Budget pool = every candidate for every domain, deduplicated by name.
        for organ in candidates:
            if all(o.name != organ.name for o in per_domain):
                per_domain.append(organ)
    allocation = allocate_budget(per_domain, budget, min_credibility=min_credibility)
    # Map back: the first selected organ that can honor each domain wins.
    selected_by_name = {o.name: o for o in per_domain if o.name in allocation.selected}
    for domain in domains:
        cands = [o for o in _candidates_for(organs, domain) if o.name in selected_by_name]
        if cands:
            # Highest value (merit-per-cost) among the affordable candidates.
            best = min(cands, key=lambda o: (-_value(o), o.name))
            chosen[domain] = best.name
    return chosen, allocation


def _candidates_for(organs: list[OrganDescriptor], domain: str) -> list[OrganDescriptor]:
    """Organs that can honor ``domain`` (exact → purpose → none), mirroring the resolver.

    Returns an empty list when nothing fits (unlike the resolver's fall-to-everything,
    which we must NOT do under a budget: an un-honorable domain must be treated
    as unfundable, not silently handed to an arbitrary organ).
    """
    exact = [o for o in organs if domain in o.domains]
    if exact:
        return exact
    purpose = [
        o for o in organs
        if o.dossier is not None and domain.lower() in o.dossier.purpose.lower()
    ]
    return purpose