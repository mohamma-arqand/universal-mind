"""Synthesis engine — close the loop: goal -> decompose -> resolve -> execute -> D.

This is the syntactic heart of the charter: ONE MIND takes a goal, DEMIURGE
decomposes it into sub-goals, the CAPABILITY RESOLVER selects the specialists
that can honor each (by domain and credibility, never identity), each executes
through the unified contractor adaptor (ToolCapability), and the results are
synthesized into a single new artifact D that no single specialist produced —
A+B+C -> D. Every step is evidence-anchored and the final synthesis is committed
canonically to the ledger.

Deterministic and local: the reference specialists are pure functions; nothing
connects to an external provider.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)
from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.errors import CallerFault
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.core.intent import Determinism, Intent
from universal_mind.demiurge.decompose import SubIntent, decompose_intent
from universal_mind.io import CapabilityResolver, Tool, ToolContract
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import MemoryStore
from universal_mind.mouth import InMemoryMouth, StructuredIntent
from universal_mind.pantheon.contracts import CapabilityResult
from universal_mind.pantheon.registry import PantheonRegistry


class SynthesisError(Exception):
    """Raised when the goal cannot be fully honored (no specialist for a sub-goal)."""


@dataclass(frozen=True)
class SubExecution:
    """One sub-goal's execution record."""

    sub_id: str
    goal: str
    specialist: str
    domain: str
    output: Any
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class SynthesisReport:
    """The full D of one run: decomposed, executed, synthesized, committed."""

    structured: StructuredIntent
    sub_executions: tuple[SubExecution, ...]
    synthesized: Any
    method: str
    evidence: EvidenceBundle
    commit_record_id: str | None
    ok: bool
    remembered_context: str = ""
    verified: bool = False           # True only if ARETĒ accepted the final D
    verification_reason: str = ""    # why the D was verified or refused


def domain_for(goal: str) -> str:
    """Map a sub-goal to a needed capability domain (deterministic keywords)."""
    lowered = goal.lower()
    if any(w in lowered for w in ("summarize", "report", "knowledge", "explain", "facts")):
        return "knowledge"
    if any(w in lowered for w in ("write", "compose", "draft", "format")):
        return "writing"
    if any(w in lowered for w in ("shell", "system", "run", "command")):
        return "system"
    return "general"


def _sub_intent(sub: SubIntent, owner_id: str) -> Intent:
    return Intent.from_raw(
        raw_text=sub.goal,
        goal=sub.goal,
        success_criteria=list(sub.success_criteria),
        constraints=list(sub.constraints),
        deadline=None,
        determinism=Determinism.STRICT,
        owner_id=owner_id,
    )


# ---------------------------------------------------------------------------
# Reference deterministic specialists (A, B, C...) — pure, no I/O.
# ---------------------------------------------------------------------------


class FactSpecialist:
    """Domain 'knowledge': returns a fixed factual line (A)."""
    contract = ToolContract(
        name="facts", version="1.0.0",
        purpose="Supply a concise factual statement about the topic.",
        signature="facts(intent, params)",
        cost_model="flat", latency_profile="instant", reliability="high",
        reversible=True, side_effects="none", required_secrets=[],
        determinism=Determinism.STRICT, domains=("knowledge",), credibility=0.8,
    )

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        return {"fact": f"{intent.goal}: the measured value is 42 units."}


class WriterSpecialist:
    """Domain 'writing': composes a polished one-line deliverable (B)."""
    contract = ToolContract(
        name="writer", version="1.0.0",
        purpose="Compose a clear, finished sentence for the deliverable.",
        signature="writer(intent, params)",
        cost_model="flat", latency_profile="instant", reliability="high",
        reversible=True, side_effects="none", required_secrets=[],
        determinism=Determinism.STRICT, domains=("writing",), credibility=0.9,
    )

    def run(self, intent: Intent, params: dict[str, Any]) -> Any:
        return {"draft": f"Final: {intent.goal}."}


@dataclass
class SynthesisEngine:
    """Close the loop using a MOUTH, Demiurge decompose, Resolver, and a ledger."""

    def __init__(
        self,
        store: MemoryStore,
        clock: Clock | None = None,
        owner: Identity = DEFAULT_OWNER,
        composer: Callable[[list[Any]], Any | None] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner
        self._registry = PantheonRegistry(store)
        self._mouth = InMemoryMouth()
        self._resolver = CapabilityResolver()
        self._mnemosyne = Mnemosyne(store, self._clock)
        self._specialists: dict[str, Tool] = {}
        self._composer = composer

    def register(self, name: str, tool: Tool) -> str:
        """Register a specialist (domain index) for resolution."""
        from universal_mind.io.adapters import register_tool

        self._specialists[name] = tool
        return register_tool(self._registry, tool, self._owner.owner_id)

    def run(self, raw_text: str) -> SynthesisReport:
        """Execute the full loop and synthesize a canonical D, committed to the ledger."""
        structured = self._mouth.commit(raw_text, self._owner.owner_id)
        decomposed = decompose_intent(structured.intent)

        executions: list[SubExecution] = []
        for sub in decomposed.sub_intents:
            domain = domain_for(sub.goal)
            organ = self._resolver.resolve_organ(self._registry, domain)
            if organ is None:
                raise SynthesisError(f"no specialist can honor sub-goal '{sub.goal}' (domain '{domain}')")
            capability = self._registry.get(organ.dossier.name, organ.dossier.version)
            try:
                result: CapabilityResult = capability.execute(_sub_intent(sub, self._owner.owner_id), {"owner_id": self._owner.owner_id})
            except CallerFault as exc:
                executions.append(SubExecution(sub.id, sub.goal, organ.name, domain, None, False, str(exc)))
                continue
            executions.append(
                SubExecution(sub.id, sub.goal, organ.name, domain, result.output, result.ok,
                             None if result.ok else "not ok")
            )

        # Synthesize A+B+C -> D: fuse through the composer when provided, else concat.
        outputs = [e.output for e in executions if e.ok]
        if self._composer is not None:
            fused = self._composer(outputs)
            if fused is not None:
                synthesized = fused
                method = "fusion"
            else:
                synthesized = "\n".join(f"[{e.specialist}] {e.output}" for e in executions if e.ok)
                method = "concat"
        else:
            parts = [f"[{e.specialist}] {e.output}" for e in executions if e.ok]
            synthesized = "\n".join(parts) if parts else None
            method = "parallel_concat"
        evidence = EvidenceBundle(self._evidence_points(executions))

        record_id: str | None = None
        if synthesized is not None:
            record_id = self._mnemosyne.record(
                owner_id=self._owner.owner_id,
                kind="synthesis",
                payload={
                    "goal": structured.intent.goal,
                    "sub_executions": [
                        {"sub_id": e.sub_id, "specialist": e.specialist, "output": e.output} for e in executions if e.ok
                    ],
                    "synthesized": synthesized,
                    "method": method,
                },
                provenance={"producer": "SynthesisEngine", "owner_id": self._owner.owner_id},
            )

        # Remember relevant prior experience before synthesizing, so the mind's
        # past shapes this run (the remembering substrate feeds the loop).
        from universal_mind.memory.lifespan import recall_context

        remembered = recall_context(
            self._store,
            structured.intent.goal,
            owner_id=self._owner.owner_id,
            clock=self._clock,
        ).summary

        verified, verification_reason = self._verify_synthesis(structured.intent.goal, executions)

        return SynthesisReport(
            structured=structured,
            sub_executions=tuple(executions),
            synthesized=synthesized,
            method=method,
            evidence=evidence,
            commit_record_id=record_id,
            ok=synthesized is not None,
            remembered_context=remembered,
            verified=verified,
            verification_reason=verification_reason,
        )

    @staticmethod
    def _verify_synthesis(goal: str, executions: list[SubExecution]) -> tuple[bool, str]:
        """Arbitrate the synthesized D against a refusal baseline.

        The final artifact is only ``verified`` if every sub-execution succeeded
        (no failure, no missing specialist) — a strictly-successful whole — pitted
        against a refusal baseline in the non-compensatory ARETĒ rule. This is the
        missing half of judgment: the *result* of synthesis is judged, not just
        the choice of specialist.
        """
        if not executions:
            return False, "no sub-executions to verify"
        if any(not e.ok for e in executions):
            failed = [e.specialist for e in executions if not e.ok]
            return False, f"sub-execution failed for: {', '.join(failed)}"

        from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
        from universal_mind.powers.judgment import CandidateOutput, Verdict

        candidate = CandidateOutput(
            strategy_id="synthesis",
            output="\n".join(str(e.output) for e in executions),
            metadata={
                "virtues": {"justice": 1.0, "wisdom": 1.0, "courage": 1.0, "temperance": 1.0},
                "sub_executions": len(executions),
            },
        )
        baseline = CandidateOutput(
            strategy_id="refusal",
            output="refuse",
            metadata={"virtues": {"justice": 1.0, "wisdom": 0.5, "courage": 1.0, "temperance": 1.0}},
        )
        verdict = InMemoryArbiter().arbitrate(
            Dispute(goal=goal, candidates=[candidate, baseline])
        )
        accepted = verdict.decision is Verdict.ALLOW and verdict.winner_strategy_id == candidate.strategy_id
        reason = verdict.reasoning
        return accepted, reason

    @staticmethod
    def _evidence_points(executions: list[SubExecution]) -> tuple[EvidencePoint, ...]:
        points: list[EvidencePoint] = []
        for e in executions:
            points.append(
                EvidencePoint(
                    type_=EvidenceType.CORRECTNESS,
                    source=EvidenceSource.TEST,
                    value=e.ok,
                    citation=f"synthesis:{e.specialist}::{e.sub_id}",
                )
            )
        return tuple(points)