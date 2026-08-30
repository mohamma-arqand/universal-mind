"""Executive Mind orchestrates intents through registered capabilities."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, cast

logger = logging.getLogger(__name__)

from ..feedback.channel import HumanFeedbackGate
from ..gates import (
    DefaultPowerZero,
    Gate,
    LayeringGate,
    PipelineJudgment,
    PowerZero,
    PrecedencePipeline,
    Verdict,
)
from ..memory.mnemosyne import Mnemosyne
from ..observability.recorder import NullRecorder, Recorder
from ..pantheon.contracts import Capability
from ..pantheon.registry import CapabilityDossier, PantheonRegistry
from .clock import Clock
from .errors import CallerFault, ErrorHandler, SystemFault, TaskFailure
from .identity import DEFAULT_OWNER, Identity
from .intent import Determinism, Intent
from .models import ExecutionRecord


class Decision(Enum):
    """Strategic decision outcomes (legacy compatibility)."""
    PROCEED = 'proceed'
    BLOCK = 'block'
    REDIRECT = 'redirect'


@dataclass
class StrategicDecision:
    """Result of a strategic decision gate evaluation (legacy compatibility)."""

    decision: Decision
    redirect_capability: str | None = None
    reason: str | None = None


class StrategicGate:
    """Base class for strategic decision gates (legacy compatibility).

    New code should implement the Gate protocol from universal_mind.gates.base.
    """

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        """Evaluate whether to proceed, block, or redirect an intent.

        Override in subclasses to implement custom decision logic.
        """
        return StrategicDecision(decision=Decision.PROCEED)


class ExecutionThrottle:
    """Throttle execution based on concurrency and error-rate policy."""

    def __init__(self, max_concurrent: int = 10, error_rate_threshold: float = 0.1):
        self.max_concurrent = max_concurrent
        self.error_rate_threshold = error_rate_threshold

    def should_allow(self, recent_errors: int, recent_executions: int, caller_faults: int = 0) -> bool:
        """Determine whether execution should proceed under throttle policy.

        Caller faults (invalid input, contract violations) are excluded from the
        error-rate calculation: they are not system failures and must not trip the
        throttle. Only ``TaskFailure``/``SystemFault`` records count as errors.
        """
        if recent_executions >= self.max_concurrent:
            return False
        effective_errors = max(0, recent_errors - caller_faults)
        error_rate = effective_errors / max(recent_executions, 1)
        return error_rate <= self.error_rate_threshold


@dataclass(frozen=True)
class RiskPolicy:
    """Configurable policy for RiskGate evaluation.

    Defaults preserve the original hardcoded behavior:
    - high risk blocks UNLESS (reversible AND strict determinism)
    - low/medium risk always proceeds
    """
    allow_high_risk_if_reversible_and_strict: bool = True
    high_risk_blocks: bool = True
    medium_risk_blocks: bool = False
    low_risk_blocks: bool = False


class RiskPolicyProtocol(Protocol):
    """Protocol defining the interface for risk evaluation policies.

    Implementations must provide an ``allows`` method that returns True if
    the given risk level should be allowed to proceed, False if it should
    be blocked.
    """
    def allows(self, risk_level: str, dossier: CapabilityDossier | None, intent: Intent) -> bool:
        """Return True if execution should proceed, False to block."""
        ...


class DefaultRiskPolicy:
    """Default risk policy preserving the original hardcoded behavior.

    - high risk blocks UNLESS (reversible AND strict determinism)
    - low/medium risk always proceeds
    """

    def __init__(self, policy: RiskPolicy | None = None):
        self.policy = policy or RiskPolicy()

    def allows(self, risk_level: str, dossier: CapabilityDossier | None, intent: Intent) -> bool:
        if risk_level == 'high':
            if self.policy.high_risk_blocks:
                # Exception: reversible + strict determinism
                return (
                    self.policy.allow_high_risk_if_reversible_and_strict
                    and dossier is not None
                    and dossier.reversible
                    and intent.determinism == Determinism.STRICT
                )
            return True
        elif risk_level == 'medium' and self.policy.medium_risk_blocks or risk_level == 'low' and self.policy.low_risk_blocks:
            return False
        return True


class RiskAssessor:
    """Assess the risk level of executing an intent via a capability."""

    def assess(self, intent: Intent, capability: Capability, dossier: CapabilityDossier) -> str:
        """Return risk level: 'low', 'medium', or 'high'."""
        if dossier.reliability == 'low':
            return 'high'
        if dossier.failure_modes != 'none':
            return 'medium'
        if intent.determinism != Determinism.STRICT:
            return 'medium'
        return 'low'


# =============================================================================
# NEW UNIFIED GATE ADAPTERS
# =============================================================================

class _RiskGateAdapter(Gate):
    """Adapts RiskAssessor + RiskPolicy to the unified Gate protocol."""

    def __init__(
        self,
        assessor: RiskAssessor,
        selector: Callable[[], tuple[CapabilityDossier, Capability]],
        policy: RiskPolicyProtocol,
        name: str = "Risk",
        precedence: int = 600,
    ):
        self._assessor = assessor
        self._selector = selector
        self._policy = policy
        self._name = name
        self._precedence = precedence

    @property
    def precedence(self) -> int:
        return self._precedence

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        intent = context.get('intent')
        if intent is None:
            raise ValueError("RiskGate requires 'intent' in context")

        dossier, capability = self._selector()
        risk_level = self._assessor.assess(intent, capability, dossier)
        context['risk_level'] = risk_level
        context['dossier'] = dossier

        if self._policy.allows(risk_level, dossier, intent):
            return Verdict.ALLOW
        return Verdict.DENY


class _HumanFeedbackGateAdapter(Gate):
    """Adapts HumanFeedbackGate to the unified Gate protocol."""

    def __init__(
        self,
        feedback_gate: HumanFeedbackGate,
        target_record_id: str | None = None,
        name: str = "HumanFeedback",
        precedence: int = 400,
    ):
        self._feedback_gate = feedback_gate
        self._target_record_id = target_record_id
        self._name = name
        self._precedence = precedence

    @property
    def precedence(self) -> int:
        return self._precedence

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        target_id = self._target_record_id or context.get('target_record_id')
        if target_id and self._feedback_gate.is_blocked(target_id):
            return Verdict.DENY
        return Verdict.ALLOW


class _PolicyGateAdapter(Gate):
    """Adapts a legacy StrategicGate to the unified Gate protocol."""

    def __init__(
        self,
        strategic_gate: StrategicGate,
        name: str = "Policy",
        precedence: int = 800,
    ):
        self._strategic_gate = strategic_gate
        self._name = name
        self._precedence = precedence

    @property
    def precedence(self) -> int:
        return self._precedence

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        intent = context.get('intent')
        if intent is None:
            raise ValueError("PolicyGate requires 'intent' in context")

        decision = self._strategic_gate.evaluate(intent, context)
        if decision.decision == Decision.PROCEED:
            return Verdict.ALLOW
        elif decision.decision == Decision.BLOCK:
            # Store the reason for the trace
            context['_last_block_reason'] = decision.reason
            return Verdict.DENY
        elif decision.decision == Decision.REDIRECT:
            # REDIRECT treated as DEFER - pipeline continues but signals redirect
            context['redirect_capability'] = decision.redirect_capability
            context['_last_redirect_reason'] = decision.reason
            return Verdict.DEFER
        return Verdict.DENY


# =============================================================================
# THIN ADAPTER: CompositeStrategicGate delegates to PrecedencePipeline
# =============================================================================

class CompositeStrategicGate(StrategicGate):
    """Thin adapter: delegates to unified PrecedencePipeline.

    This maintains backward compatibility with existing code that expects
    a StrategicGate, while using the single authoritative pipeline.

    The pipeline order (highest precedence first):
    - PowerZero: 1000 (absolute veto)
    - LayeringGate: 900 (layer boundary enforcement)
    - Policy: 800 (caller-supplied business logic)
    - Risk: 600 (risk assessment)
    - HumanFeedback: 400 (historical rejection)

    Throttle is NOT part of this pipeline; applied separately after.

    Backward compatibility: Can also be initialized with a list of
    (precedence, StrategicGate) tuples as in the original implementation.
    """

    def __init__(
        self,
        # Backward compatibility: allow old-style list of tuples as first positional arg
        gates: list[tuple[int, StrategicGate]] | None = None,
        # New-style: named parameters (no gate_precedence — fixed by GATE_PRECEDENCE)
        power_zero: PowerZero | None = None,
        layering_gate: LayeringGate | None = None,
        policy_gate: StrategicGate | None = None,
        risk_assessor: RiskAssessor | None = None,
        risk_selector: Callable[[], tuple[CapabilityDossier, Capability]] | None = None,
        risk_policy: RiskPolicyProtocol | None = None,
        feedback_gate: HumanFeedbackGate | None = None,
        target_record_id: str | None = None,
    ):
        # Detect old-style initialization: first arg is a list of tuples
        if gates is not None and isinstance(gates, list):
            # Old-style: list of (precedence, StrategicGate) tuples
            self._init_legacy(gates)
        else:
            # New-style: named parameters (gate_precedence removed - fixed policy)
            self._power_zero = power_zero or DefaultPowerZero()
            self._layering_gate = layering_gate
            self._policy_gate = policy_gate or StrategicGate()
            self._risk_assessor = risk_assessor or RiskAssessor()
            self._risk_selector = risk_selector
            self._risk_policy = risk_policy or DefaultRiskPolicy()
            self._feedback_gate = feedback_gate
            self._target_record_id = target_record_id

            # Build the unified pipeline
            self._pipeline = self._build_pipeline()
            self._last_judgment: PipelineJudgment | None = None

    def _init_legacy(self, gates: list[tuple[int, StrategicGate]]) -> None:
        """Initialize from legacy list of (precedence, StrategicGate) tuples.

        Combines all legacy gates into a single "Policy" gate that runs them
        in order of their original precedence (highest first).
        """
        from ..gates.precedence import create_default_pipeline

        # Sort legacy gates by precedence (highest first)
        sorted_gates = sorted(gates, key=lambda x: -x[0])

        # Create a composite StrategicGate that runs all legacy gates in order
        class CompositeLegacyGate(StrategicGate):
            def __init__(self, gates: list[tuple[int, StrategicGate]]):
                self._gates = gates

            def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
                for precedence, gate in self._gates:
                    decision = gate.evaluate(intent, context)
                    if decision.decision != Decision.PROCEED:
                        return decision
                return StrategicDecision(decision=Decision.PROCEED)

        composite_gate = CompositeLegacyGate(sorted_gates)

        # Build pipeline with just PowerZero, Layering (disabled), Policy (composite), no Risk, no HumanFeedback
        self._pipeline = create_default_pipeline(
            power_zero=DefaultPowerZero(),
            risk_gate=None,
            strategic_gate=_PolicyGateAdapter(composite_gate, name="Policy"),
            human_feedback_gate=None,
            layering_gate=None,  # No layering in legacy mode
        )

        # Set dummy values for new-style attributes (not used in legacy mode)
        self._power_zero = DefaultPowerZero()
        self._layering_gate = None
        self._policy_gate = StrategicGate()
        self._risk_assessor = RiskAssessor()
        self._risk_selector = None
        self._risk_policy = DefaultRiskPolicy()
        self._feedback_gate = None
        self._target_record_id = None
        self._gate_precedence = {}

    def _build_pipeline(self) -> PrecedencePipeline:
        """Build the unified PrecedencePipeline using frozen GATE_PRECEDENCE."""
        from ..gates.precedence import create_default_pipeline

        # Use create_default_pipeline which respects GATE_PRECEDENCE
        return create_default_pipeline(
            power_zero=self._power_zero,
            risk_gate=_RiskGateAdapter(
                self._risk_assessor,
                self._risk_selector,
                self._risk_policy,
                name="Risk",
            ) if self._risk_selector is not None else None,
            strategic_gate=_PolicyGateAdapter(
                self._policy_gate,
                name="Policy",
            ),
            human_feedback_gate=_HumanFeedbackGateAdapter(
                self._feedback_gate,
                target_record_id=self._target_record_id,
                name="HumanFeedback",
            ) if self._feedback_gate is not None else None,
            layering_gate=self._layering_gate,
        )

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        """Evaluate via unified pipeline, convert to legacy StrategicDecision."""
        # Ensure intent is in context
        context = dict(context)
        context['intent'] = intent

        judgment: PipelineJudgment = self._pipeline.evaluate(context)
        # Expose the raw trace so ExecutiveMind can record per-gate decisions
        # without re-running the pipeline (pure side-channel).
        self._last_judgment = judgment

        # Convert unified verdict to legacy StrategicDecision
        if judgment.decision == Verdict.ALLOW:
            return StrategicDecision(decision=Decision.PROCEED)
        elif judgment.decision == Verdict.DENY:
            # Find the gate that caused the DENY - use stored reason from context if available
            reason = "Blocked by gate pipeline"
            for result in judgment.trace:
                if result.verdict == Verdict.DENY and not result.skipped:
                    # Check if the adapter stored a specific reason in context
                    if context.get('_last_block_reason'):
                        reason = f"Blocked by {result.gate_name}: {context['_last_block_reason']}"
                    else:
                        reason = f"Blocked by {result.gate_name}: {result.reason}"
                    break
            return StrategicDecision(decision=Decision.BLOCK, reason=reason)
        elif judgment.decision == Verdict.DEFER:
            redirect_cap = context.get('redirect_capability')
            redirect_reason = context.get('_last_redirect_reason', "Deferred by gate pipeline")
            return StrategicDecision(
                decision=Decision.REDIRECT,
                redirect_capability=redirect_cap,
                reason=redirect_reason,
            )
        return StrategicDecision(decision=Decision.BLOCK, reason="Unknown verdict")


# Legacy constants (kept for backward compatibility)
# New code should use gate.precedence directly
PRECEDENCE_POLICY = 800
PRECEDENCE_RISK = 600
PRECEDENCE_FEEDBACK = 400


class ThrottleGate(StrategicGate):
    """Gate that blocks when the throttle policy disallows execution."""

    def __init__(self, throttle: ExecutionThrottle, memory: Mnemosyne, owner_id: str):
        self.throttle = throttle
        self.memory = memory
        self.owner_id = owner_id

    @staticmethod
    def _fault_metrics(memory: Mnemosyne, owner_id: str) -> tuple[int, int, int]:
        """Return (total_fault_count, execution_count, caller_fault_count) for an owner.

        ``total_fault_count`` counts all ``fault`` records (task, system, AND
        caller). ``caller_fault_count`` is the subset of those that are caller
        faults, tracked separately so :meth:`ExecutionThrottle.should_allow` can
        subtract them from the error rate.
        """
        records = [h.record for h in memory.recall(owner_id=owner_id)]
        total_fault_count = 0
        caller_fault_count = 0
        execution_count = 0
        for record in records:
            kind = record.get('kind')
            if kind == 'fault':
                total_fault_count += 1
                if record.get('payload', {}).get('fault_class') == 'caller_fault':
                    caller_fault_count += 1
            elif kind in ('intent_received', 'capability_selected'):
                execution_count += 1
        return total_fault_count, execution_count, caller_fault_count

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        errors, executions, caller_faults = self._fault_metrics(self.memory, self.owner_id)
        if not self.throttle.should_allow(errors, executions, caller_faults):
            return StrategicDecision(
                decision=Decision.BLOCK,
                reason=(
                    f'Throttled: {errors} errors, {executions} executions, '
                    f'{caller_faults} caller faults'
                ),
            )
        return StrategicDecision(decision=Decision.PROCEED)


class RiskGate(StrategicGate):
    """Gate that blocks high-risk operations using :class:`RiskAssessor` output.

    The assessor computes the risk level from the selected capability; the
    capability is resolved lazily through ``selector`` (a zero-arg callable that
    returns ``(dossier, capability)``) so the gate only does the work when it
    actually runs and can defer capability selection until policy gates before it
    have already returned PROCEED.

    Policy is configurable via any object implementing :class:`RiskPolicyProtocol`.
    The default is :class:`DefaultRiskPolicy`, which preserves the original
    hardcoded behavior:
    - high risk blocks UNLESS (reversible AND strict determinism)
    - low/medium risk always proceeds

    The computed risk level is written back into ``context['risk_level']`` and
    ``context['dossier']`` for downstream steps and the audit trail.
    """

    def __init__(
        self,
        assessor: RiskAssessor,
        selector: Callable[[], tuple[CapabilityDossier, Capability]],
        policy: RiskPolicyProtocol | None = None,
    ):
        self.assessor = assessor
        self.selector = selector
        self.policy = policy or DefaultRiskPolicy()

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        dossier, capability = self.selector()
        risk_level = self.assessor.assess(intent, capability, dossier)
        context['risk_level'] = risk_level
        context['dossier'] = dossier

        if self.policy.allows(risk_level, dossier, intent):
            return StrategicDecision(decision=Decision.PROCEED)
        return StrategicDecision(
            decision=Decision.BLOCK,
            reason=f'{risk_level.capitalize()} risk execution blocked by policy: risk_level={risk_level}',
        )


class HumanFeedbackGateWrapper(StrategicGate):
    """Gate that blocks intents targeting a record previously rejected by a human."""

    def __init__(self, feedback_gate: HumanFeedbackGate, target_record_id: str | None = None):
        self.feedback_gate = feedback_gate
        self.target_record_id = target_record_id

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        target_id = self.target_record_id or context.get('target_record_id')
        if target_id and self.feedback_gate.is_blocked(target_id):
            return StrategicDecision(
                decision=Decision.BLOCK,
                reason=f'Blocked by human feedback: {target_id}',
            )
        return StrategicDecision(decision=Decision.PROCEED)


class ExecutiveMind:
    """Coordinates intent handling, delegation, and audit trails.

    The pre-execution pipeline in :meth:`handle` is, in order:

    1. Contract validation (``Intent.assert_complete`` / ``validates_params``)
    2. CompositeStrategicGate (policy + risk + human feedback)
    3. Throttle
    4. Execute (with idempotency-gated retries and fallback chain)
    5. Record result

    Capability selection and capability-level ``validate_intent`` run as part of
    the risk sub-gate (which needs the dossier) and again right before execution.
    """

    def __init__(
        self,
        registry: PantheonRegistry,
        memory: Mnemosyne,
        clock: Clock,
        owner: Identity = DEFAULT_OWNER,
        error_handler: ErrorHandler | None = None,
        strategic_gate: StrategicGate | None = None,
        risk_assessor: RiskAssessor | None = None,
        risk_policy: RiskPolicyProtocol | None = None,
        throttle: ExecutionThrottle | None = None,
        feedback_gate: HumanFeedbackGate | None = None,
        power_zero: PowerZero | None = None,
        layering_gate: LayeringGate | None = None,
        *,
        recorder: Recorder | None = None,
    ) -> None:
        self.registry = registry
        self.memory = memory
        self.clock = clock
        self.owner = owner
        self.error_handler = error_handler or ErrorHandler()
        self.risk_assessor = risk_assessor or RiskAssessor()
        self.risk_policy = risk_policy or DefaultRiskPolicy()
        self.throttle = throttle or ExecutionThrottle()
        self.feedback_gate = feedback_gate
        self.power_zero = power_zero or DefaultPowerZero()
        self.layering_gate = layering_gate
        # The caller-supplied gate, if any, becomes the policy sub-gate of the
        # composite. If none is supplied, an always-PROCEED gate is used.
        self.strategic_gate = strategic_gate or StrategicGate()
        # Observability: recorder is a side-channel. A default is never shared
        # as a mutable class attribute; each instance builds a fresh NullRecorder.
        self._recorder = recorder or NullRecorder()
        # Count of recorder failures. Must never affect control flow; it exists
        # so a broken observer can be detected instead of silently ignored.
        self._recorder_failures = 0

    def _build_composite_gate(self, selector: Callable[[], tuple[CapabilityDossier, Capability]]) -> CompositeStrategicGate:
        """Assemble the composite gate using unified PrecedencePipeline.

        ``selector`` is a zero-arg callable resolving ``(dossier, capability)``;
        it is handed to the risk gate adapter for lazy risk assessment.

        Gate precedence is fixed by GATE_PRECEDENCE module constant from gates.precedence:
        - PowerZero: absolute veto authority
        - Layering: layer boundary enforcement
        - Policy: caller-supplied business logic
        - Risk: risk assessment
        - HumanFeedback: historical rejection

        Throttle is NOT part of this pipeline; applied separately after.
        """
        from ..gates.precedence import resolve_order

        # Verify the frozen precedence order
        expected_order = resolve_order()
        assert expected_order == (
            "PowerZero",
            "Layering",
            "Policy",
            "Risk",
            "HumanFeedback"
        ), f"Unexpected precedence order: {expected_order}"

        return CompositeStrategicGate(
            power_zero=self.power_zero,
            layering_gate=self.layering_gate,
            policy_gate=self.strategic_gate,
            risk_assessor=self.risk_assessor,
            risk_selector=selector,
            risk_policy=self.risk_policy,
            feedback_gate=self.feedback_gate,
            target_record_id=None,  # Will be set from gate_context in handle()
        )

    def handle(self, intent: Intent) -> ExecutionRecord:
        """Execute an intent through a selected capability and audit every step."""
        # Step 1: contract validation (caller-fault branch). Raises IntentIncomplete
        # (a CallerFault) for invalid input and records nothing, so repeated bad
        # intents cannot accumulate error-rate history.
        intent.assert_complete()
        intent.validates_params({'owner_id': intent.owner_id})

        intent_record_id = self.memory.record(
            owner_id=intent.owner_id,
            kind='intent_received',
            payload=intent.to_payload(),
            provenance={'producer': 'ExecutiveMind', 'stage': 'received'},
        )

        try:
            # Lazy capability resolution memoized across the pipeline so the risk
            # sub-gate and the execution phase share one selection.
            _selected: dict[str, Any] = {}

            def select() -> tuple[CapabilityDossier, Capability]:
                if not _selected:
                    dossier = self._select_capability(intent)
                    _selected['dossier'] = dossier
                    _selected['capability'] = self.registry.get(dossier.name, dossier.version)
                return _selected['dossier'], _selected['capability']

            # Step 2: composite strategic gate (policy + risk + human feedback).
            composite_gate = self._build_composite_gate(select)
            gate_context = {
                'intent_record_id': intent_record_id,
                'target_record_id': intent_record_id,
            }
            strategic_decision = composite_gate.evaluate(intent, gate_context)

            # Observability (side-channel): record each evaluated gate's decision.
            # Only gates that actually ran are recorded — gates short-circuited by
            # an earlier DENY produce no event. A Recorder failure must never
            # swallow a gate decision or change the veto path, so it is caught.
            self._record_gate_decisions(composite_gate)

            if strategic_decision.decision == Decision.BLOCK:
                return self._record_block(
                    intent.owner_id, intent_record_id,
                    strategic_decision.reason or 'Blocked by strategic gate',
                    status='blocked',
                    terminal_gate=self._denying_gate(composite_gate),
                )

            # Step 2 (resume): resolve the selected capability for execution.
            dossier, capability = select()
            capability.validate_intent(intent)

            if strategic_decision.decision == Decision.REDIRECT and strategic_decision.redirect_capability:
                redirect_dossier = self._find_capability_by_name(strategic_decision.redirect_capability)
                if redirect_dossier is not None:
                    dossier = redirect_dossier
                    capability = self.registry.get(dossier.name, dossier.version)

            risk_level = gate_context.get('risk_level', 'low')

            # Step 3: throttle (evaluated explicitly after the gate so its policy is
            # configurable and observable independent of the strategic decision).
            errors, executions, caller_faults = ThrottleGate._fault_metrics(
                self.memory, intent.owner_id
            )
            if not self.throttle.should_allow(errors, executions, caller_faults):
                return self._record_block(
                    intent.owner_id, intent_record_id,
                    f'Throttled: {errors} errors, {executions} executions, {caller_faults} caller faults',
                    status='blocked',
                    terminal_gate='Throttle',
                )

            self.memory.record(
                owner_id=intent.owner_id,
                kind='risk_assessment',
                payload={'risk_level': risk_level, 'capability': dossier.name},
                provenance={'producer': 'ExecutiveMind', 'stage': 'risk_assessment'},
            )

            selected_record_id = self.memory.record(
                owner_id=intent.owner_id,
                kind='capability_selected',
                payload={'name': dossier.name, 'version': dossier.version, 'signature': dossier.signature},
                provenance={'producer': 'ExecutiveMind', 'stage': 'selected'},
            )
            params = {'owner_id': intent.owner_id}

            # Step 4: execute with idempotency-gated retries and fallback chain.
            result = self._execute_with_retries(capability, intent, params, dossier)

            result_record_id = self.memory.record(
                owner_id=intent.owner_id,
                kind='capability_result',
                payload={
                    'ok': result.ok,
                    'output': result.output,
                    'cost': result.cost,
                    'provenance': result.provenance,
                    'notes': list(result.notes),
                },
                provenance={'producer': 'ExecutiveMind', 'stage': 'result'},
            )
            cycle_status = 'ok' if result.ok else 'not_ok'
            self._safe_record(
                'executive.cycle',
                outcome=cycle_status,
                terminal_gate=None,
            )
            return ExecutionRecord(
                intent_record_id=intent_record_id,
                capability_record_id=selected_record_id,
                result_record_id=result_record_id,
                fault_record_id=None,
                status=cycle_status,
                notes=result.notes,
            )
        except CallerFault as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'caller_fault'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            self._safe_record('executive.cycle', outcome='caller_fault', terminal_gate=None)
            raise
        except TaskFailure as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'task_failure'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            self._safe_record('executive.cycle', outcome='task_failure', terminal_gate=None)
            raise
        except SystemFault as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'system_fault'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            self._safe_record('executive.cycle', outcome='system_fault', terminal_gate=None)
            raise

    def _record_block(self, owner_id: str, intent_record_id: str, reason: str, status: str,
                      terminal_gate: str | None = None) -> ExecutionRecord:
        decision_record_id = self.memory.record(
            owner_id=owner_id,
            kind='strategic_decision',
            payload={'decision': 'block', 'reason': reason},
            provenance={'producer': 'ExecutiveMind', 'stage': 'strategic_gate'},
        )
        self._safe_record(
            'executive.cycle',
            outcome=status,
            terminal_gate=terminal_gate,
        )
        return ExecutionRecord(
            intent_record_id=intent_record_id,
            capability_record_id=None,
            result_record_id=None,
            fault_record_id=decision_record_id,
            status=status,
            notes=(reason,),
        )

    @property
    def recorder_failures(self) -> int:
        """Number of Recorder failures encountered (read-only observability)."""
        return self._recorder_failures

    def _safe_record(self, event: str, **fields: object) -> None:
        """Record to the observability Recorder without affecting control flow.

        The Recorder is an observability side-channel: if it raises, the error is
        swallowed so a broken recorder cannot change cycle semantics (fail-open).
        The failure is *not* silent: it is counted on :attr:`recorder_failures`
        and surfaced via a module-level ``logging.warning`` with the traceback.
        Neither the counter nor the log alters the veto path or handler output.
        """
        try:
            self._recorder.record(event, **fields)
        except Exception:
            self._recorder_failures += 1
            logger.warning('Recorder raised while recording %r; event dropped (fail-open).', event, exc_info=True)

    def _record_gate_decisions(self, composite_gate: CompositeStrategicGate) -> None:
        """Record per-gate verdicts exposed by the unified pipeline trace.

        Only gates that actually ran are recorded. When an earlier gate returns
        DENY the pipeline short-circuits and later gates are marked ``skipped``;
        those produce no ``gate.decision`` event (no gate decision was made).

        Fields:
          gate (name), delay_ms (precedence as a delay proxy), skipped, allowed.
        """
        judgment = cast("PipelineJudgment | None", getattr(composite_gate, '_last_judgment', None))
        if judgment is None:
            return
        for result in judgment.trace:
            if result.skipped:
                continue
            self._safe_record(
                'gate.decision',
                gate=result.gate_name,
                delay_ms=result.precedence,
                skipped=result.skipped,
                allowed=(result.verdict == Verdict.ALLOW),
            )

    def _denying_gate(self, composite_gate: CompositeStrategicGate) -> str | None:
        """Return the name of the first gate that denied execution, if any."""
        judgment = cast("PipelineJudgment | None", getattr(composite_gate, '_last_judgment', None))
        if judgment is None:
            return None
        for result in judgment.trace:
            if result.verdict == Verdict.DENY and not result.skipped:
                return result.gate_name
        return None

    def _find_capability_by_name(self, name: str) -> CapabilityDossier | None:
        for dossier in self.registry.search():
            if dossier.name == name:
                return dossier
        return None

    def _execute_with_retries(self, capability: Capability, intent: Intent, params: dict[str, Any], dossier: CapabilityDossier) -> Any:
        """Execute with retries, idempotency gating, backoff, and a fallback chain.

        Retry policy:
        * Retries only apply when the selected capability ``dossier.idempotent`` is
          True. Non-idempotent capabilities fail fast on the first non-system error.
        * ``TaskFailure`` is retried (if idempotent); ``SystemFault`` and
          ``CallerFault`` are never retried.
        * Exponential backoff with jitter is applied before each retry (configurable
          via ``ErrorHandler.retry_policy``).
        * After retries are exhausted, each capability in the configured fallback
          chain is tried once, in order.

        Fallback behavior:
        * Each fallback capability's ``validate_intent`` is called before ``execute``.
          If validation fails (raises ``ContractViolation`` or other ``CallerFault``),
          that fallback is skipped and the chain continues.
        * Only ``TaskFailure`` and ``SystemFault`` from a fallback execution cause
          the chain to continue to the next fallback. ``CallerFault`` (including
          ``ContractViolation``) propagates immediately and is NOT caught.
        * The strategic gate and throttle are NOT re-evaluated for fallbacks; this
          is intentional to keep fallback execution fast and deterministic. The
          original capability selection already passed these checks.
        """
        is_idempotent = dossier.idempotent
        primary_exception: Exception | None = None  # The original error from the primary capability

        for attempt in range(self.error_handler.effective_retry_policy.max_retries + 1):
            try:
                return capability.execute(intent, params)
            except (SystemFault, CallerFault) as exc:
                if primary_exception is None:
                    primary_exception = exc
                break  # never retry these
            except TaskFailure as exc:
                if primary_exception is None:
                    primary_exception = exc
                if not is_idempotent:
                    break  # fail fast: non-idempotent capability
                if not self.error_handler.should_retry(attempt, exc):
                    break
                delay = self.error_handler.effective_retry_policy.get_delay(attempt)
                if delay > 0:
                    self.error_handler.sleep(delay)

        # If we never had an exception (shouldn't happen), raise a generic error
        if primary_exception is None:
            primary_exception = TaskFailure("Execution failed with no exception captured")

        # Fallback chain: try each configured fallback capability once, in order.
        fallback_error: Exception | None = None
        for fallback_name, fallback_params in self.error_handler.get_fallback_chain():
            fallback_dossier = self._find_capability_by_name(fallback_name)
            if fallback_dossier is None:
                continue
            try:
                fallback_capability = self.registry.get(fallback_dossier.name, fallback_dossier.version)
                # Validate intent for fallback - if it rejects, skip this fallback
                fallback_capability.validate_intent(intent)
                return fallback_capability.execute(intent, {**params, **fallback_params})
            except (TaskFailure, SystemFault) as exc:
                # Only continue chain on TaskFailure or SystemFault
                fallback_error = exc
                continue
            except CallerFault:
                # CallerFault (including ContractViolation) propagates immediately
                raise
            except BaseException as exc:  # noqa: BLE001
                # Unexpected errors - treat as SystemFault and continue chain
                fallback_error = SystemFault(f"Unexpected error in fallback {fallback_name}: {exc}")
                fallback_error.__cause__ = exc
                continue

        # All fallbacks failed (or no fallbacks configured). Re-raise the ORIGINAL
        # primary exception, chaining the last fallback error as __cause__ for context.
        if fallback_error is not None:
            raise primary_exception from fallback_error
        raise primary_exception

    def _select_capability(self, intent: Intent) -> CapabilityDossier:
        """Choose a capability dossier for an intent.

        Selection order:
        1. Exact dossier-name match against ``intent.goal``.
        2. Substring match of ``intent.goal`` against name/signature/purpose.
        3. Fallback to the first registered dossier (determinism-agnostic).
        """
        dossiers = list(self.registry.search())
        if not dossiers:
            raise TaskFailure(f'No capabilities registered to handle intent goal: {intent.goal!r}.')
        goal = intent.goal.lower()
        for dossier in dossiers:
            if dossier.name == intent.goal:
                return dossier
        for dossier in dossiers:
            blob = f"{dossier.name} {dossier.signature} {dossier.purpose}".lower()
            if goal and goal in blob:
                return dossier
        return dossiers[0]