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
    ) -> None:
        self._store = store
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner
        self._registry = PantheonRegistry(store)
        self._mouth = InMemoryMouth()
        self._resolver = CapabilityResolver()
        self._mnemosyne = Mnemosyne(store, self._clock)
        self._specialists: dict[str, Tool] = {}

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

        # Synthesize A+B+C -> D (concatenate the specialist outputs into one artifact).
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

        return SynthesisReport(
            structured=structured,
            sub_executions=tuple(executions),
            synthesized=synthesized,
            method=method,
            evidence=evidence,
            commit_record_id=record_id,
            ok=synthesized is not None,
        )

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