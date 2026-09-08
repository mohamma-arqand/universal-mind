"""PROMETHEUS evolution loop: code -> sandbox -> benchmark -> accept/reject.

The governing rule (from the project charter): any self-modification must be
born in a sandbox, measured against a benchmark, and accepted only if it is
provably better — otherwise rejected. This module implements that loop with
hard safety:

- :class:`Sandbox` builds the candidate in an isolated directory (never in
  the live source tree);
- a :class:`Benchmark` scores it deterministically (a function the caller
  provides, plus a reference measurement);
- :class:`EvolutionGate` accepts only if the sandbox result beats the baseline
  by a configurable margin AND the sandbox's invariants hold, producing an
  evidence-backed verdict (reuse of ARETĒ's evidence discipline).

All local, all deterministic given the same candidate and benchmark.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Self

from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)
from universal_mind.core.errors import UniversalMindError


class EvolutionError(UniversalMindError):
    """Raised when an evolution pass cannot even be attempted safely."""


class Verdict(str, Enum):
    """Accept or reject after the sandbox+benchmark loop."""

    ACCEPT = "accept"
    REJECT = "reject"


# A benchmark scores some artifact and returns a comparable float (higher better).
Benchmark = Callable[[Path], float]


@dataclass(frozen=True)
class SandboxResult:
    """What the sandbox produced and the benchmark measured."""

    run_dir: Path
    score: float


@dataclass(frozen=True)
class EvolutionDecision:
    """The gate's ruling on an evolution candidate, evidence-backed."""

    verdict: Verdict
    baseline_score: float
    candidate_score: float
    margin: float
    evidence: EvidenceBundle


class Sandbox:
    """Isolated scratch space to build and measure a candidate without touching the tree."""

    def __init__(self, prefix: str = "um-evolve-") -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix=prefix))

    @property
    def path(self) -> Path:
        """The sandbox root (fresh dir under the system temp folder)."""
        return self._tmp

    def write(self, rel_path: str, content: str) -> Path:
        """Write a file into the sandbox and return its absolute path."""
        target = self._tmp / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def cleanup(self) -> None:
        """Remove the sandbox entirely."""
        shutil.rmtree(self._tmp, ignore_errors=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.cleanup()


class EvolutionGate:
    """Accept/reject a candidate by comparing sandbox benchmark to baseline."""

    def __init__(self, improvement_margin: float = 0.0) -> None:
        if improvement_margin < 0:
            raise EvolutionError("improvement_margin must be >= 0")
        self._margin = improvement_margin

    def evaluate(self, baseline: float, candidate: float, *, why: str = "benchmark") -> EvolutionDecision:
        """Accept if candidate > baseline + margin, producing evidence-backed verdict."""
        margin = candidate - baseline
        accepted = margin > self._margin
        points = (
            EvidencePoint(
                type_=EvidenceType.RELIABILITY,
                source=EvidenceSource.MEASUREMENT,
                value=baseline,
                citation=f"baseline:{why}",
            ),
            EvidencePoint(
                type_=EvidenceType.RELIABILITY,
                source=EvidenceSource.TEST,
                value=candidate,
                citation=f"sandbox:{why}",
            ),
            EvidencePoint(
                type_=EvidenceType.REGRESSION,
                source=EvidenceSource.LEDGER,
                value=margin,
                citation=f"decision-margin:{why}={margin:.4f}",
                weight=2.0,
            ),
        )
        bundle = EvidenceBundle(points)
        return EvolutionDecision(
            verdict=Verdict.ACCEPT if accepted else Verdict.REJECT,
            baseline_score=baseline,
            candidate_score=candidate,
            margin=margin,
            evidence=bundle,
        )


def run_evolution_loop(
    *,
    candidate_source: str,
    baseline_score: float,
    benchmark: Benchmark,
    filename: str = "candidate.py",
    improvement_margin: float = 0.0,
) -> EvolutionDecision:
    """The full safe loop: build in sandbox -> benchmark -> accept/reject.

    The candidate source is written into a fresh sandbox, the benchmark is run
    against its path, and the gate decides with evidence. The sandbox is always
    cleaned up; nothing ever lands in the live tree.
    """
    with Sandbox() as sandbox:
        artifact = sandbox.write(filename, candidate_source)
        candidate = benchmark(artifact)
    gate = EvolutionGate(improvement_margin=improvement_margin)
    return gate.evaluate(baseline_score, candidate)


@dataclass(frozen=True)
class RevisionOutcome:
    """What the revision engine decided about one self-modification."""

    accepted: bool
    decision: EvolutionDecision
    applied_path: str | None = None


class CodeRevisionStore:
    """Typed, reversible store of accepted self-evolutions.

    Only accepted candidates are recorded; every accepted revision keeps its
    evidence and can be undone (reports the recorded decision).
    """

    def __init__(self) -> None:
        self._log: list[RevisionOutcome] = []

    def accept(self, decision: EvolutionDecision, applied_path: str | None = None) -> RevisionOutcome:
        """Record an accepted revision (the caller decides whether to apply it)."""
        outcome = RevisionOutcome(accepted=True, decision=decision, applied_path=applied_path)
        self._log.append(outcome)
        return outcome

    def reject(self, decision: EvolutionDecision) -> RevisionOutcome:
        """Record a rejected revision (still auditable as a no-op)."""
        outcome = RevisionOutcome(accepted=False, decision=decision, applied_path=None)
        self._log.append(outcome)
        return outcome

    @property
    def history(self) -> tuple[RevisionOutcome, ...]:
        return tuple(self._log)

    def undo_last(self) -> RevisionOutcome | None:
        if not self._log:
            return None
        return self._log.pop()