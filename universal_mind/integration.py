"""Integration face — compose the subsystems into one closed loop.

The standalone subsystems (ExecutiveMind, Gateway, ARETĒ, Prometheus) are
each verified in isolation. This module wires them into a single runnable
loop so a caller experiences the whole system:

1. an intent is executed by the real :class:`~universal_mind.core.executive.ExecutiveMind`
   through a :class:`GatewayCapability` that reaches outward via a
   :class:`~universal_mind.io.gateway.Gateway` provider chain;
2. the produced output is arbitrated against a baseline by ARETĒ (a virtue
   rubric — non-compensatory);
3. Prometheus watches the same memory ledger and returns evolution proposals
   (proposals-only / safe by default).

Everything is deterministic with an injected provider and clock, so the
composition is testable and provable from the outside.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from universal_mind.arete import ArbitrationVerdict, Dispute, InMemoryArbiter
from universal_mind.core.clock import Clock, SystemClock
from universal_mind.core.errors import SystemFault, TaskFailure
from universal_mind.core.executive import ExecutiveMind
from universal_mind.core.identity import DEFAULT_OWNER, Identity
from universal_mind.core.intent import Determinism, Intent
from universal_mind.io.gateway import Gateway, Message
from universal_mind.memory.mnemosyne import Mnemosyne
from universal_mind.memory.store import InMemoryStore, MemoryStore
from universal_mind.pantheon.contracts import (
    Capability,
    CapabilityResult,
    ContractViolation,
)
from universal_mind.pantheon.registry import CapabilityDossier, PantheonRegistry
from universal_mind.powers.judgment import CandidateOutput
from universal_mind.prometheus import EvolutionReport, InMemoryPrometheus


class GatewayCapability(Capability):
    """A capability that turns an intent into a provider call through a Gateway."""

    def __init__(self, gateway: Gateway) -> None:
        self._gateway = gateway

    def validate_intent(self, intent: Intent) -> None:
        """Require a creatable/strict intent with a non-empty prompt."""
        if intent.determinism not in (Determinism.CREATIVE, Determinism.STRICT):
            raise ContractViolation(f"Invalid determinism level: {intent.determinism}")
        if not (intent.raw_text or intent.goal):
            raise ContractViolation("GatewayCapability needs raw_text or goal as the prompt")

    def execute(self, intent: Intent, params: dict[str, Any]) -> CapabilityResult:
        prompt = intent.raw_text or intent.goal
        outcome = self._gateway.generate([Message(role="user", content=prompt)])
        if not outcome.ok:
            raise TaskFailure(outcome.last_error or "provider chain failed")
        return CapabilityResult(
            ok=True,
            output={
                "content": outcome.content,
                "provider": outcome.provider_name,
                "attempts": outcome.attempts,
                "cost": outcome.cost,
            },
            cost={"currency": "provider_units", "amount": float(outcome.cost)},
            provenance={"producer": "GatewayCapability", "provider": outcome.provider_name},
            notes=(f"served by {outcome.provider_name}",),
        )


@dataclass(frozen=True)
class IntegrationReport:
    """The composable result of one end-to-end integration run."""

    execution_status: str
    result_content: str | None
    result_provider: str | None
    arbitration: ArbitrationVerdict
    evolution_summary: str
    proposals: tuple[str, ...]
    ok: bool


class IntegrationError(Exception):
    """Raised when a composed run cannot complete."""


@runtime_checkable
class UniversalMindRuntime(Protocol):
    """The high-level face of the composed system."""

    def run(self, goal: str, raw_text: str) -> IntegrationReport:
        """Execute an intent end-to-end and report the composed outcome."""
        ...


class InMemoryIntegrationHarness:
    """Reference composed runtime — deterministic with an injected Gateway."""

    def __init__(
        self,
        gateway: Gateway,
        *,
        store: MemoryStore | None = None,
        clock: Clock | None = None,
        owner: Identity = DEFAULT_OWNER,
    ) -> None:
        self._store = store if store is not None else InMemoryStore()
        self._clock = clock if clock is not None else SystemClock()
        self._owner = owner

        self._registry = PantheonRegistry(self._store)
        self._capability = GatewayCapability(gateway)
        self._register_generate(owner)

        self._memory = Mnemosyne(self._store, self._clock)
        self._executive = ExecutiveMind(
            registry=self._registry,
            memory=self._memory,
            clock=self._clock,
            owner=owner,
        )
        self._arbiter = InMemoryArbiter()
        self._prometheus = InMemoryPrometheus(self._store)

    @property
    def store(self) -> MemoryStore:
        """The shared ledger (readable for assertions/audit)."""
        return self._store

    def _register_generate(self, owner: Identity) -> None:
        """Register the 'generate' capability, idempotently across reopens.

        On a durable (on-disk) ledger the registry restores the *dossier* from
        the stored registration record, but capability objects (code) cannot be
        serialized, so the live instance is re-attached rather than re-registered
        (which would raise on the duplicate key and append a duplicate record).
        """
        dossier = CapabilityDossier(
            name="generate",
            version="1.0.0",
            signature="generate(intent, params)",
            purpose="Produce a provider-backed response through the Gateway.",
            cost_model="flat",
            latency_profile="normal",
            reliability="high",
            side_effects="none",
            reversible=True,
            required_secrets=[],
            failure_modes="none",
            dependencies=[],
            determinism=Determinism.CREATIVE,
            idempotent=True,
            provenance={
                "producer": "integration",
                "created_at": self._clock.now().isoformat(),
                "owner_id": owner.owner_id,
                "explicit_fields": ["idempotent", "determinism"],
            },
        )
        try:
            attached = self._registry.restore_capability("generate", "1.0.0", self._capability)
        except SystemFault:
            attached = False
        if not attached:
            self._registry.register(dossier, self._capability)

    def run(self, goal: str, raw_text: str) -> IntegrationReport:
        """Execute one intent through the composed ExecutiveMind + Gateway.

        Raises:
            IntegrationError: if execution fails (the exception surfaces so the
                caller can decide; the ledger still holds the fault record).
        """
        intent = Intent.from_raw(
            goal=goal,
            raw_text=raw_text,
            success_criteria=[f"output responds to {goal}"],
            constraints=[],
            owner_id=self._owner.owner_id,
            determinism=Determinism.CREATIVE,
        )
        try:
            record = self._executive.handle(intent)
        except Exception as exc:
            raise IntegrationError(str(exc)) from exc

        content = self._last_result_content()
        provider = self._last_result_provider()

        # ARETĒ: arbitrate the produced output against a plain baseline echo.
        candidates = [
            CandidateOutput(
                strategy_id="gateway",
                output=content or "",
                metadata={
                    "virtues": self._virtue_observation(
                        produced=bool(content),
                        attempts=self._last_result_attempts(),
                    )
                },
            ),
            CandidateOutput(
                strategy_id="baseline",
                output=raw_text,
                metadata={"virtues": {}},
            ),
        ]
        verdict = self._arbiter.arbitrate(
            Dispute(goal=goal, candidates=candidates, context={})
        )

        evolution: EvolutionReport = self._prometheus.evolve()
        proposals = tuple(p.kind.value for p in evolution.proposals)

        return IntegrationReport(
            execution_status=record.status,
            result_content=content,
            result_provider=provider,
            arbitration=verdict,
            evolution_summary=evolution.summary,
            proposals=proposals,
            ok=record.status == "ok",
        )

    def _last_result_content(self) -> str | None:
        content = self._last_result_field("content")
        return str(content) if content is not None else None

    def _last_result_provider(self) -> str | None:
        provider = self._last_result_field("provider")
        return str(provider) if provider is not None else None

    def _last_result_attempts(self) -> int:
        attempts = self._last_result_field("attempts")
        if isinstance(attempts, (int, float)):
            return int(attempts)
        return 1

    @staticmethod
    def _virtue_observation(produced: bool, attempts: int) -> dict[str, float]:
        """Deterministic virtue observation from *execution quality*.

        Encodes real pipeline signals (did the provider produce a result; how
        many attempts it took) as cardinal-virtue scores, so ARETĒ compares the
        strategies on how well the pipeline served, not on text-keyword
        guessing. Always in [0, 1].
        """
        reliable = 0.9 if produced else 0.1
        measured = max(0.3, 0.9 - 0.1 * max(0, attempts - 1))
        return {
            "wisdom": reliable,       # produced knowledge
            "courage": 0.9,           # honestly sourced/accountable by default
            "temperance": measured,   # fewer retries = more measured
            "justice": 0.9,           # no rights violated by default
        }

    def _last_result_field(self, key: str) -> Any:
        records = list(self._store.read_all())
        for record in reversed(records):
            if record.get("kind") == "capability_result":
                output = record.get("payload", {}).get("output", {})
                if isinstance(output, dict) and key in output:
                    return output[key]
        return None