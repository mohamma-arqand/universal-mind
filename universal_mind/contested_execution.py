"""Contested execution — two candidate chains race, ARETĒ picks the winner.

The advisor recommends ONE chain; but a recommendation untested against a rival
is a guess. This module closes that gap: for a command, build the advisor's
route PLUS a plausible rival (a chain built from the same capability words in a
different order/composition), run BOTH for real, and let the same non-compensatory
VirtueArbiter that governs specialist disputes pick the binding winner.

Honest rules:
- Fewer than two distinct candidates → no contest, the single route runs as-is
  (never fabricate a straw-man rival out of nothing).
- Both outcomes are returned; the verdict carries WHY (excellence + scores).
- A disqualified candidate can never win, even on raw excellence ties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from universal_mind.arete.run_judgment import judge_run


@dataclass(frozen=True)
class ContestEntry:
    """One candidate chain's real run + its ARETĒ scorecard."""

    route: tuple[str, ...]
    payload: dict[str, Any]
    excellence: float
    scores: dict[str, float]
    disqualified: bool
    disqualify_reason: str


@dataclass(frozen=True)
class ContestVerdict:
    """The binding outcome of a contested execution."""

    winner: ContestEntry | None
    loser: ContestEntry | None
    contested: bool  # False when only one candidate existed (no honest rival)
    reasoning: str
    all_entries: tuple[ContestEntry, ...] = field(default_factory=tuple)


def _rival_route(route: tuple[str, ...], words: set[str], registry_caps: set[str]) -> tuple[str, ...] | None:
    """A plausible rival chain from the same evidence — or None (no straw men).

    Rival heuristics, honest by construction:
    - a chain that ALSO serves the routed capabilities but in the other order
      (consumer-first vs producer-first matters with the dataflow active);
    - the advisor's own route is never its own rival.
    """
    if len(route) < 2:
        return None
    reversed_route = tuple(reversed(route))
    if reversed_route == route or not (words & set(route)):
        return None
    return reversed_route


def run_contested(
    command: str,
    route: tuple[str, ...],
    run_route: Any,  # callable(route: tuple[str, ...]) -> payload dict
    words: set[str] | None = None,
) -> ContestVerdict:
    """Run the advised chain and its honest rival; ARETĒ picks the winner.

    ``run_route`` is an injected executor (route_and_run's core) so this module
    stays deterministic and testable. The rival is the reversed chain — with the
    dataflow active, order genuinely changes the artifact, so this is a real
    contest, not theater.
    """
    words = words if words is not None else set(route)
    rival = _rival_route(route, words, set(route))

    if rival is None:
        payload = run_route(route)
        entry = _entry_for(route, payload)
        return ContestVerdict(
            winner=entry, loser=None, contested=False,
            reasoning="تنها یک نامزد بود — مسابقه‌ای در کار نیست",
            all_entries=(entry,),
        )

    payloads = [run_route(route), run_route(rival)]
    entries = [_entry_for(r, p) for r, p in ((route, payloads[0]), (rival, payloads[1]))]

    # Non-compensatory ranking: not-disqualified first, then excellence, then
    # SYNTHESIS — a run whose outputs actually fused (flows recorded) is more
    # than the sum of its parts, per the project's own charter.
    def _synthesis(e: ContestEntry) -> int:
        flows = e.payload.get("flows") or []
        return len(flows) if isinstance(flows, list) else 0

    ranked = sorted(
        entries,
        key=lambda e: (not e.disqualified, e.excellence, _synthesis(e)),
        reverse=True,
    )
    winner, loser = ranked[0], ranked[1]
    if (
        winner.excellence == loser.excellence
        and winner.disqualified == loser.disqualified
        and _synthesis(winner) == _synthesis(loser)
    ):
        # A true tie: DEFER to the advised route (the operator's learned signal)
        # and say so honestly — never break a tie with a coin flip.
        if winner.route != route:
            winner, loser = loser, winner
        reasoning = "تساوی کامل — مسیر توصیهشده برگزیده شد"
    elif winner.excellence == loser.excellence and _synthesis(winner) > _synthesis(loser):
        reasoning = (
            f"تساوی داوری — سنتز تعیینکننده بود: {' → '.join(winner.route)} "
            f"خروجیها را در هم ادغام کرد ({_synthesis(winner)} جریان در برابر {_synthesis(loser)})"
        )
    else:
        reasoning = (
            f"برنده: {' → '.join(winner.route)} با داوری {winner.excellence:.2f} "
            f"در برابر {loser.excellence:.2f}"
        )
    return ContestVerdict(
        winner=winner, loser=loser, contested=True,
        reasoning=reasoning, all_entries=tuple(entries),
    )


def _entry_for(route: tuple[str, ...], payload: dict[str, Any]) -> ContestEntry:
    judgment = judge_run(payload)
    return ContestEntry(
        route=route,
        payload=payload,
        excellence=float(judgment.get("excellence", 0.0)),
        scores=dict(judgment.get("scores", {})),
        disqualified=bool(judgment.get("disqualified", False)),
        disqualify_reason=str(judgment.get("disqualify_reason", "")),
    )


__all__ = ["ContestEntry", "ContestVerdict", "run_contested"]