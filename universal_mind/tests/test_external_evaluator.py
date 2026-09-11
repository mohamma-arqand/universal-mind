"""Tests for the independent evaluator — the second judge outside the loop."""

from __future__ import annotations

from universal_mind.arete.external_evaluator import (
    AuditFinding,
    evaluate_loop,
)
from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def _loop_with_judgments() -> SelfAwarenessLoop:
    from universal_mind.powers.judgment import CandidateOutput

    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    loop.consider(CandidateOutput(strategy_id="a", output="x", metadata={
        "virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}}))
    return loop


def test_healthy_loop_passes_foreign_rubric() -> None:
    loop = _loop_with_judgments()
    result = evaluate_loop(loop)
    assert result.passed is True
    assert result.score == 1.0
    assert any(f.dimension == "acceptance_bar_bounded" for f in result.findings)
    assert any(f.dimension == "self_correction_reversible" for f in result.findings)


def test_audit_records_external_audit_in_ledger() -> None:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    result = evaluate_loop(loop, store=store)
    assert result.ledger_record_id is not None
    kinds = [r.get("kind") for r in store.read_all()]
    assert "external_audit" in kinds


def test_fresh_loop_has_no_lineage_evidence() -> None:
    """A fresh loop with no judgments fails the lineage-evidence dimension."""
    loop = _loop()
    result = evaluate_loop(loop)
    lineage_finding = next(f for f in result.findings if f.dimension == "lineage_has_evidence")
    assert lineage_finding.ok is False


def test_result_is_deterministic() -> None:
    a = evaluate_loop(_loop())
    b = evaluate_loop(_loop())
    assert a.summary == b.summary
    assert a.score == b.score


def test_finding_is_frozen_dataclass() -> None:
    f = AuditFinding("x", True, "note")
    assert f.dimension == "x" and f.ok is True and f.note == "note"