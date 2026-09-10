"""Tests for the lifecycle loop — mint → remember → consent."""

from __future__ import annotations

from typing import Any

from universal_mind.feedback import HumanVerdict
from universal_mind.lifecycle import Lifecycle
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.power_zero import PowerZero


def _lifecycle(consent: Any | None = None) -> Lifecycle:
    PowerZero.reset_minted()
    return Lifecycle(InMemoryStore(), consent=consent)


def test_full_loop_accepts_and_remembers() -> None:
    """A working power is minted, remembered, and (with consent) promoted."""
    lc = _lifecycle(consent=lambda p, k: HumanVerdict.CONSENT)
    turn = lc.run("probe-loop", "a loop power")
    assert turn.generated.accepted is True
    assert turn.remembered is True
    assert turn.promoted is True


def test_remembered_is_false_when_rejected() -> None:
    """A rejected power never enters the ledger, so nothing is remembered."""
    generator = __import__("universal_mind.powers.generator", fromlist=["PowerZeroGenerator"]).PowerZeroGenerator(
        benchmark=lambda fn, expected: 0.0
    )
    lc = Lifecycle(InMemoryStore(), consent=lambda p, k: HumanVerdict.CONSENT, generator=generator)
    turn = lc.run("bad-loop", "will fail")
    assert turn.generated.accepted is False
    assert turn.remembered is False
    assert turn.promoted is False


def test_deny_by_default_blocks_promotion_but_still_remembers() -> None:
    """Without consent the power is remembered but not promoted."""
    lc = _lifecycle()  # deny-by-default
    turn = lc.run("probe-pending", "pending power")
    assert turn.generated.accepted is True
    assert turn.remembered is True
    assert turn.promoted is False
    assert turn.consent_outcome.human_verdict is HumanVerdict.VETO


def test_consent_record_lands_in_ledger() -> None:
    lc = _lifecycle(consent=lambda p, k: HumanVerdict.CONSENT)
    lc.run("probe-consent", "recorded power")
    kinds = [r.get("kind") for r in lc._store.read_all()]
    assert "generated_power" in kinds
    assert "human_consent" in kinds


def test_two_turns_mint_distinct_powers() -> None:
    lc = _lifecycle(consent=lambda p, k: HumanVerdict.CONSENT)
    t1 = lc.run("power-a", "first")
    t2 = lc.run("power-b", "second")
    assert t1.generated.minted is not None
    assert t2.generated.minted is not None
    assert t1.generated.minted.name == "power-a"
    assert t2.generated.minted.name == "power-b"
    names = PowerZero.get_precedence()
    assert "power-a" in names and "power-b" in names