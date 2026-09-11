"""Tests for the self-awareness loop — the mind closes its own meta loop."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.judgment import CandidateOutput


def _candidate(strategy_id: str, wisdom: float) -> CandidateOutput:
    return CandidateOutput(
        strategy_id=strategy_id,
        output=f"artifact-{strategy_id}",
        metadata={
            "virtues": {"justice": 1.0, "wisdom": wisdom, "courage": 1.0, "temperance": 1.0}
        },
    )


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def test_healthy_loop_reports_no_correction() -> None:
    loop = _loop()
    loop.consider(_candidate("a", 0.9))
    loop.consider(_candidate("b", 0.95))
    result = loop.introspect()
    assert result.action_taken is False


def test_unhealthy_defer_spiral_triggers_self_correction() -> None:
    loop = _loop()
    # Produce a lineage that defers repeatedly, then introspect.
    from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode

    nodes = [
        JudgmentNode(depth=0, contender=f"c{i}", decision="deferred", reasoning="r", excellence=0.5, justice=1.0)
        for i in range(6)
    ]
    loop._lineage = JudgmentLineage.from_nodes(loop._lineage.keeper, nodes)
    result = loop.introspect()
    assert result.action_taken is True
    assert loop.acceptance_bar > 0.9
    assert loop.budget < 100.0


def test_self_correction_is_persistent_and_auditable() -> None:
    loop = _loop()
    from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode

    nodes = [
        JudgmentNode(depth=0, contender=f"c{i}", decision="deferred", reasoning="r", excellence=0.5, justice=1.0)
        for i in range(6)
    ]
    loop._lineage = JudgmentLineage.from_nodes(loop._lineage.keeper, nodes)
    result = loop.introspect()
    assert result.ledger_record_id is not None
    # The correction is recorded as a self_awareness entry in the ledger.
    kinds = [r.get("kind") for r in loop._store.read_all()]
    assert "self_awareness" in kinds


def test_acceptance_bar_and_budget_are_exposed_reactive_state() -> None:
    loop = _loop()
    assert loop.acceptance_bar == 0.9
    assert loop.budget == 100.0
    loop.introspect()  # healthy (insufficient) — no change
    bar1, budget1 = loop.acceptance_bar, loop.budget
    assert bar1 == 0.9
    assert budget1 == 100.0


def test_insufficient_decisions_is_not_unhealthy() -> None:
    loop = _loop()
    loop.consider(_candidate("only-one", 0.9))
    result = loop.introspect()
    assert result.action_taken is False
    assert result.healthy is True


def test_consider_records_reasoned_lineage() -> None:
    loop = _loop()
    loop.consider(_candidate("x", 0.92))
    loop.consider(_candidate("y", 0.97))
    assert len(loop.lineage.nodes()) == 2