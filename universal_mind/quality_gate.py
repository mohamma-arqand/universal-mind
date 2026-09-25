"""The quality gate — a weak first run triggers self-repair, not resignation.

The platform already judges every run (ARETĒ). This module CLOSES the loop:
when the verdict on the primary route is weak (below the excellence bar or
disqualified), the platform does not hand the operator a bad artifact — it
re-runs through the honest rival routes and keeps the best REAL verdict.
This is self-repair through search, grounded in the project's own charter:
judgment must change behavior, not merely grade it.

Honest rules:
- The FIRST run's verdict is never thrown away — every attempt is returned.
- Self-repair only fires on a WEAK verdict; a strong verdict passes untouched
  (no wasted double-runs of already-excellent work).
- Every repaired run is recorded to history so the advisor learns which route
  actually won (evidence-based, not a guess).
- When every candidate is weak, the BEST weak one wins and is labeled as such
  — never a fabricated success.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from universal_mind.arete.run_judgment import judge_run

# Below this ARETĒ excellence the run is "weak" and triggers self-repair.
_DEFAULT_BAR = 0.75


@dataclass(frozen=True)
class GateAttempt:
    """One real attempt: the route, its payload, and its ARETĒ verdict."""

    route: tuple[str, ...]
    payload: dict[str, Any]
    excellence: float
    disqualified: bool
    primary: bool = False


@dataclass(frozen=True)
class GateOutcome:
    """The gate's decision: what ran, what was repaired, what ships."""

    attempts: tuple[GateAttempt, ...]
    shipped: GateAttempt  # the attempt the operator receives
    repaired: bool  # self-repair fired and changed the shipped attempt
    reasoning: str


def _verdict_of(payload: dict[str, Any]) -> tuple[float, bool]:
    judgment = judge_run(payload)
    return float(judgment.get("excellence", 0.0)), bool(judgment.get("disqualified", False))


def run_with_quality_gate(
    command: str,
    route: tuple[str, ...],
    runner: Callable[[tuple[str, ...]], dict[str, Any]],
    *,
    bar: float = _DEFAULT_BAR,
    max_attempts: int = 3,
    _primary_payload: dict[str, Any] | None = None,
) -> GateOutcome:
    """Run the planned route; if ARETĒ grades it weak, repair through rivals.

    ``runner`` executes one route through the real engine and returns its
    payload (the same shape route_and_run produces). The candidate set is the
    planned route plus its honest re-orderings (producer-first variants).
    """
    attempts: list[GateAttempt] = []
    seen: set[tuple[str, ...]] = set()

    # R46-13 — THE PRIMARY IS THE RUN WE ALREADY HAVE: the caller ran the
    # planned route before calling the gate; re-running it here doubled
    # every command's history rows and wasted the hot path. The existing
    # payload becomes the primary attempt; rivals run only on weakness.
    if _primary_payload is not None:
        excellence0, disqualified0 = _verdict_of(_primary_payload)
        attempts.append(GateAttempt(
            route=route, payload=_primary_payload,
            excellence=excellence0, disqualified=disqualified0,
            primary=True,
        ))
        if not disqualified0 and excellence0 >= bar:
            return GateOutcome(
                attempts=tuple(attempts), shipped=attempts[0],
                repaired=False,
                reasoning=f"داوری {excellence0:.2f} — از دروازهی کیفیت گذشت (بدون رانِ دوباره)",
            )

    # THREE honest candidates: the advised route, its reverse, and a
    # planner-style rotation (first→last) for 3+ chains. Each is REAL work —
    # never a straw man; duplicates are de-duplicated.
    candidates: list[tuple[str, ...]] = [route]
    if len(route) >= 2:
        reversed_route = tuple(reversed(route))
        if reversed_route != route:
            candidates.append(reversed_route)
    if len(route) >= 3:
        rotated = (route[-1], *route[:-1])
        if rotated not in candidates:
            candidates.append(rotated)

    # THE FARTHEST-FIRST RIVAL: when the command names no order, a
    # best-scoring alternative from the intent lens joins the set — a rival
    # that is genuinely DIFFERENT, not a reshuffle of the same words. It
    # never runs when it loses the lens or the sentence is explicit.
    try:
        from universal_mind.intent_lens import rank_routes

        if len(route) >= 2 and len(candidates) < max_attempts:
            # every acceptable permutation the planner already knows
            import itertools

            perms = list(itertools.permutations(route))
            lens_ranked = rank_routes(perms, command)
            for alt in lens_ranked:
                if alt.route not in candidates and alt.score > 0.30:
                    candidates.append(alt.route)
                    break
    except Exception:  # noqa: BLE001 — the gate never blocks on a lens
        pass

    for candidate in candidates[:max(1, max_attempts)]:
        if candidate in seen:
            continue
        seen.add(candidate)
        payload = runner(candidate)
        excellence, disqualified = _verdict_of(payload)
        attempts.append(GateAttempt(
            route=candidate, payload=payload,
            excellence=excellence, disqualified=disqualified,
            primary=(len(attempts) == 0),
        ))
        # A strong primary passes the gate untouched — no wasted second run.
        if attempts[0].primary and not disqualified and excellence >= bar:
            break
        # A strong repaired candidate also stops the search.
        if not disqualified and excellence >= bar:
            break

    if not attempts:
        raise ValueError("the quality gate needs at least one attempt")

    ranked = sorted(
        attempts,
        key=lambda a: (not a.disqualified, a.excellence),
        reverse=True,
    )
    best = ranked[0]
    primary = attempts[0]
    repaired = best.route != primary.route

    if repaired:
        reasoning = (
            f"داوری مسیر اصلی {primary.excellence:.2f} بود (زیر میزان {bar:.2f}) — "
            f"ترمیم خودکار: {' → '.join(best.route)} با {best.excellence:.2f} جایگزین شد"
        )
    elif best.excellence < bar:
        reasoning = (
            f"داوری بهترین تلاش {best.excellence:.2f} بود (زیر میزان {bar:.2f}) — "
            "هر نامزد ضعیف بود؛ بهترین ضعیف ارسال میشود، نه موفقیت جعلی"
        )
    else:
        reasoning = f"داوری {best.excellence:.2f} — از دروازهی کیفیت گذشت"

    try:
        from universal_mind.session_core import SessionCore

        if repaired:
            SessionCore.current().add("repairs")
    except Exception:  # noqa: BLE001
        pass
    return GateOutcome(
        attempts=tuple(attempts), shipped=best, repaired=repaired, reasoning=reasoning,
    )


__all__ = ["GateAttempt", "GateOutcome", "run_with_quality_gate"]