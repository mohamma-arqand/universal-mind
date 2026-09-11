"""Self-awareness loop — the mind closes its own loop, then acts on what it sees.

The three meta-capabilities built so far (judgment lineage, execution budget,
judgment health) each matured in isolation. This module is the integration the
name "integrated mind" demands: one closed loop that, after every synthesis run,

1. promotes the standing standard through the reasoned ``JudgmentLineage``
   (so the *why* is kept, not just the winner),
2. self-assesses the health of its own judging (``assess_judgment_health``),
3. *acts* on unhealthy judgment — tightening the acceptance bar and shrinking
   the execution budget — rather than merely reporting it, and
4. records the whole pass as a ``self_awareness`` entry in the ledger, so the
   mind's introspection is as auditable as its judgment.

The result is the "productive narcissism" the charter gestures at: the mind
watches itself, and watching changes what it does next. Deterministic and local.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.arete.health import assess_judgment_health
from universal_mind.arete.lineage import JudgmentLineage
from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore


@dataclass(frozen=True)
class SelfAwarenessResult:
    """What one introspection pass saw, and what it changed in response."""

    healthy: bool
    health_summary: str
    action_taken: bool
    action_reason: str
    adjusted_bar: float            # acceptance bar after this pass
    adjusted_budget: float         # execution budget after this pass
    lineage_nodes: int
    ledger_record_id: str | None


class SelfAwarenessLoop:
    """Close the meta loop: judge → self-assess → self-correct → record.

    It wires the three meta-capabilities into one pass and makes the mind
    reactive to its own health: an unhealthy judgment history (too much
    deferral, or declining accepted excellence) triggers a concrete correction —
    a higher acceptance bar and a tighter budget — which is then persisted so a
    future run actually behaves more strictly.
    """

    def __init__(
        self,
        store: MemoryStore,
        keeper: StandardKeeper,
        *,
        owner: Identity = DEFAULT_OWNER,
        initial_bar: float = 0.9,
        initial_budget: float = 100.0,
    ) -> None:
        self._store = store
        self._keeper = keeper
        self._lineage = JudgmentLineage(keeper)
        self._owner = owner
        clock: Clock = keeper._clock if hasattr(keeper, "_clock") and keeper._clock is not None else SystemClock()
        self._mnemosyne = Mnemosyne(store, clock)
        self._bar = initial_bar
        self._budget = initial_budget

    # -- reactive state -----------------------------------------------------

    @property
    def acceptance_bar(self) -> float:
        """The current bar a candidate D must clear to be promoted."""
        return self._bar

    @property
    def budget(self) -> float:
        """The current execution budget available to the next synthesis."""
        return self._budget

    @property
    def lineage(self) -> JudgmentLineage:
        """The reasoned judgment history this loop maintains."""
        return self._lineage

    def consider(self, proposal: Any) -> Any:
        """Arbitrate a proposal through the lineage (records the reason)."""
        return self._lineage.consider(proposal)

    def introspect(self) -> SelfAwarenessResult:
        """Assess judgment health and, if unhealthy, tighten the bar and budget.

        The self-correction is real and persistent: ``acceptance_bar`` and
        ``budget`` are lowered-for-consumption by future passes, and the ledger
        gains a ``self_awareness`` record so the change is auditable.
        """
        health = assess_judgment_health(self._lineage)

        action_taken = False
        action_reason = ""
        if not health.unhealthy and not health.signals:
            # Too few decisions to judge — no action, but still recorded.
            action_reason = "insufficient decisions to self-correct"
        elif health.unhealthy:
            action_taken = True
            bad = ", ".join(s.name for s in health.signals if not s.ok)
            self._bar = min(1.0, self._bar + 0.03)
            self._budget = round(self._budget * 0.8, 4)
            action_reason = f"unhealthy ({bad}) → raised bar to {self._bar:.2f}, cut budget to {self._budget:.2f}"
        else:
            action_reason = "judgment healthy — no correction needed"

        record_id = self._mnemosyne.record(
            owner_id=self._owner.owner_id,
            kind="self_awareness",
            payload={
                "healthy": health.unhealthy is False,
                "health_summary": health.summary,
                "action_taken": action_taken,
                "bar": self._bar,
                "budget": self._budget,
                "lineage_depth": len(self._lineage.nodes()),
            },
            provenance={"producer": "SelfAwarenessLoop", "owner_id": self._owner.owner_id},
        )

        return SelfAwarenessResult(
            healthy=not health.unhealthy,
            health_summary=health.summary,
            action_taken=action_taken,
            action_reason=action_reason,
            adjusted_bar=self._bar,
            adjusted_budget=self._budget,
            lineage_nodes=len(self._lineage.nodes()),
            ledger_record_id=record_id,
        )

    def healthy(self) -> bool:
        """Shorthand: is the mind currently judging itself to be healthy?"""
        return assess_judgment_health(self._lineage).unhealthy is False