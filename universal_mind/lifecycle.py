"""Lifecycle loop — chain the self-augmenting capabilities into one closed flow.

The three capabilities (Power Zero, remembering Mnemosyne, human consent) are
verified in isolation. This module composes them into a single multi-turn flow
that mirrors how the mind actually grows: it *mints* a new power, *remembers*
it through Mnemosyne, and *finalizes* it through human consent over an ARETĒ
promotion — each step feeding the next, all on one canonical ledger.

Deterministic and local; no external provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.arete.standard import PromotionDecision, StandardKeeper
from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.feedback import PromotionConsent
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore
from universal_mind.powers.generator import GeneratedPower, PowerZeroGenerator
from universal_mind.powers.judgment import CandidateOutput
from universal_mind.powers.power_zero import PowerZero


@dataclass(frozen=True)
class LifecycleTurn:
    """The result of one full loop iteration over the three capabilities."""

    generated: GeneratedPower
    remembered: bool                 # Mnemosyne found the power in the ledger
    consent_outcome: Any             # ConsentOutcome (promotion gated by human)
    promoted: bool                   # net effect: a finalized improvement


class Lifecycle:
    """Drive the mind's growth loop: mint → remember → consent to promote."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        clock: Clock | None = None,
        owner: Identity = DEFAULT_OWNER,
        consent: Any | None = None,   # injectable human; default deny-by-default
        generator: PowerZeroGenerator | None = None,
    ) -> None:
        self._store = store
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner
        self._consent = consent
        self._mnemosyne = Mnemosyne(store, self._clock)
        self._keeper = StandardKeeper(store, clock=self._clock, owner=owner)
        self._generator = generator if generator is not None else PowerZeroGenerator()

    def run(self, power_name: str, description: str) -> LifecycleTurn:
        """Run one full turn: mint a power, remember it, and consent to promote it.

        1. **Mint** — PowerZeroGenerator generates, sandboxes, benchmarks, and
           arbitrates a new power. A rejected power ends the turn (nothing to
           remember or promote).
        2. **Remember** — the accepted power source is recorded in the ledger and
           Mnemosyne is asked to recall it by name; ``remembered`` is True only
           if the mind can retrieve its own creation.
        3. **Consent** — the minted power becomes a candidate for the standing
           standard, and ``PromotionConsent`` gates it on human consent — an
           ARETĒ promotion that also needs a HUMAN ruling to finalize.
        """
        generated = self._generator.generate(power_name, description)
        if not generated.accepted:
            return LifecycleTurn(
                generated=generated,
                remembered=False,
                consent_outcome=None,
                promoted=False,
            )

        # Record the creation so the mind can find it later.
        self._mnemosyne.record(
            owner_id=self._owner.owner_id,
            kind="generated_power",
            payload={"name": power_name, "description": description, "source": generated.source},
            provenance={"producer": "Lifecycle", "owner_id": self._owner.owner_id},
        )
        hits = self._mnemosyne.query(power_name, kinds=("generated_power",))
        remembered = bool(hits) and any(
            h.record.get("payload", {}).get("name") == power_name for h in hits
        )

        # Consent-gated promotion of the minted power into the standing standard.
        candidate = CandidateOutput(
            strategy_id=power_name,
            output=generated.source,
            metadata={
                "virtues": {"justice": 1.0, "wisdom": _wisdom(generated.benchmark_score),
                           "courage": 1.0, "temperance": 1.0},
                "benchmark_score": generated.benchmark_score,
            },
        )
        if self._consent is not None:
            consent = PromotionConsent(self._keeper, consent=self._consent, clock=self._clock, owner=self._owner)
        else:
            consent = PromotionConsent(self._keeper, clock=self._clock, owner=self._owner)
        outcome = consent.consider(candidate)

        promoted = (
            outcome.finalized
            and outcome.promotion_decision is PromotionDecision.PROMOTED
        )
        return LifecycleTurn(
            generated=generated,
            remembered=remembered,
            consent_outcome=outcome,
            promoted=promoted,
        )


def _wisdom(score: float) -> float:
    return max(0.1, min(1.0, score))


def mint_and_remember_and_consent(
    store: MemoryStore,
    power_name: str,
    description: str,
    *,
    consent: Any | None = None,
) -> LifecycleTurn:
    """Convenience: one call runs the full mint → remember → consent loop."""
    PowerZero.reset_minted()
    return Lifecycle(store, consent=consent).run(power_name, description)