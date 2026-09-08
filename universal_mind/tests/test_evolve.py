"""Tests for the PROMETHEUS sandbox->benchmark->accept/reject loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from universal_mind.prometheus import (
    CodeRevisionStore,
    EvolutionGate,
    Sandbox,
    Verdict,
    run_evolution_loop,
)
from universal_mind.prometheus.evolve import EvolutionError


def length_benchmark(path: Path) -> float:
    """Score = file size (a simple, deterministic benchmark)."""
    return float(path.stat().st_size)


def test_sandbox_isolates_artifact() -> None:
    """A sandbox write lands in a temp dir, never in the repo tree."""
    with Sandbox() as s:
        p = s.write("candidate.py", "x = 1\n")
        assert p.exists()
        assert s.path in p.parents
    # After exit, sandbox is cleaned up.
    assert not s.path.exists()


def test_sandbox_cleanup_on_exception() -> None:
    """Sandbox is removed even if the caller raises inside the block."""
    s = Sandbox()
    with pytest.raises(RuntimeError):
        with s:
            raise RuntimeError("boom")
    assert not s.path.exists()


def test_gate_accepts_when_better() -> None:
    """Accept requires candidate > baseline + margin."""
    gate = EvolutionGate(improvement_margin=0.0)
    d = gate.evaluate(baseline=10.0, candidate=11.5, why="size")
    assert d.verdict is Verdict.ACCEPT
    assert d.margin == pytest.approx(1.5)


def test_gate_rejects_when_not_better() -> None:
    """No improvement -> reject, with evidence."""
    gate = EvolutionGate()
    d = gate.evaluate(baseline=10.0, candidate=10.0, why="size")
    assert d.verdict is Verdict.REJECT
    assert d.evidence.points


def test_gate_enforces_margin() -> None:
    """Strict margin: candidate must exceed baseline + margin."""
    gate = EvolutionGate(improvement_margin=2.0)
    assert gate.evaluate(10.0, 11.0, why="m").verdict is Verdict.REJECT
    assert gate.evaluate(10.0, 12.5, why="m").verdict is Verdict.ACCEPT


def test_gate_require_nonnegative_margin() -> None:
    with pytest.raises(EvolutionError):
        EvolutionGate(improvement_margin=-1.0)


def test_evidence_bundle_present() -> None:
    """Every gate decision carries evidence (baseline + sandbox + margin)."""
    d = EvolutionGate().evaluate(10.0, 9.0, why="probe")
    assert len(d.evidence.points) == 3
    citations = [p.citation for p in d.evidence.points]
    assert any("baseline" in c for c in citations)
    assert any("sandbox" in c for c in citations)
    assert any("decision-margin" in c for c in citations)


def test_run_evolution_loop_end_to_end() -> None:
    """The full loop writes in a sandbox, benchmarks, and returns a verdict."""
    decision = run_evolution_loop(
        candidate_source="a" * 100,  # 100-byte candidate
        baseline_score=len("x") / 1.0,  # baseline: 1 byte
        benchmark=length_benchmark,
    )
    assert decision.verdict is Verdict.ACCEPT
    assert decision.candidate_score == 100.0


def test_revision_store_records_accept_and_reject() -> None:
    """The store records both kinds of outcomes and can undo."""
    store = CodeRevisionStore()
    gate = EvolutionGate()
    accepted = store.accept(gate.evaluate(5.0, 6.0, why="q"))
    rejected = store.reject(gate.evaluate(5.0, 5.0, why="q"))
    assert accepted.accepted
    assert not rejected.accepted
    last = store.undo_last()
    assert last is not None and not last.accepted
    assert len(store.history) == 1


def test_deterministic_gate() -> None:
    """Identical inputs to the gate produce identical verdicts."""
    d1 = EvolutionGate().evaluate(3.0, 4.0, why="x")
    d2 = EvolutionGate().evaluate(3.0, 4.0, why="x")
    assert d1.verdict == d2.verdict and d1.margin == d2.margin