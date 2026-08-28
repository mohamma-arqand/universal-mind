"""Executive Mind orchestrates intents through registered capabilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Callable, Protocol
from enum import Enum

from .clock import Clock
from .errors import SystemFault, TaskFailure, CallerFault, ErrorHandler
from .identity import Identity, DEFAULT_OWNER
from .intent import Intent, Determinism
from .models import ExecutionRecord
from ..memory.mnemosyne import Mnemosyne
from ..pantheon.registry import PantheonRegistry, CapabilityDossier
from ..pantheon.contracts import Capability
from ..feedback.channel import HumanFeedbackGate


class Decision(Enum):
    """Strategic decision outcomes."""
    PROCEED = 'proceed'
    BLOCK = 'block'
    REDIRECT = 'redirect'


@dataclass
class StrategicDecision:
    """Result of a strategic decision gate evaluation."""

    decision: Decision
    redirect_capability: Optional[str] = None
    reason: Optional[str] = None


class StrategicGate:
    """Base class for strategic decision gates."""

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
                if (self.policy.allow_high_risk_if_reversible_and_strict
                        and dossier is not None
                        and dossier.reversible
                        and intent.determinism == Determinism.STRICT):
                    return True
                return False
            return True
        elif risk_level == 'medium' and self.policy.medium_risk_blocks:
            return False
        elif risk_level == 'low' and self.policy.low_risk_blocks:
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


class CompositeStrategicGate(StrategicGate):
    """Composable strategic gate chaining sub-gates with configurable precedence.

    Sub-gates are evaluated in descending precedence order. The first sub-gate to
    return a non-PROCEED decision (BLOCK or REDIRECT) short-circuits and wins.

    This gives callers an explicit, documented precedence policy. The default
    precedence levels used by :meth:`ExecutiveMind` are:

    *  80 — policy gate (caller-supplied business logic)
    *  60 — risk gate (high-risk operation blocking)
    *  50 — human-feedback gate (historical rejection blocking)

    Throttle is deliberately NOT part of this composite: per the pre-execution
    pipeline contract, execution throttle is applied as a separate step AFTER the
    strategic gate (see :meth:`ExecutiveMind.handle`).
    """

    def __init__(self, gates: Optional[list[tuple[int, StrategicGate]]] = None):
        self.gates = sorted(gates or [], key=lambda x: -x[0])

    def evaluate(self, intent: Intent, context: dict[str, Any]) -> StrategicDecision:
        for _precedence, gate in self.gates:
            decision = gate.evaluate(intent, context)
            if decision.decision != Decision.PROCEED:
                return decision
        return StrategicDecision(decision=Decision.PROCEED)

    def add_gate(self, precedence: int, gate: StrategicGate) -> None:
        self.gates.append((precedence, gate))
        self.gates.sort(key=lambda x: -x[0])


# Precedence constants. Higher = evaluated first and can shadow lower-priority gates.
PRECEDENCE_POLICY = 80
PRECEDENCE_RISK = 60
PRECEDENCE_FEEDBACK = 50


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
        policy: Optional[RiskPolicyProtocol] = None,
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

    def __init__(self, feedback_gate: HumanFeedbackGate, target_record_id: Optional[str] = None):
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
        gate_precedence: dict[str, int] | None = None,
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
        self.gate_precedence = gate_precedence or {}
        # The caller-supplied gate, if any, becomes the policy sub-gate of the
        # composite. If none is supplied, an always-PROCEED gate is used.
        self.strategic_gate = strategic_gate or StrategicGate()

    def _build_composite_gate(self, selector: Callable[[], tuple[CapabilityDossier, Capability]]) -> CompositeStrategicGate:
        """Assemble the composite gate (policy + risk + feedback) with precedence.

        ``selector`` is a zero-arg callable resolving ``(dossier, capability)``;
        it is handed to :class:`RiskGate` for lazy risk assessment.

        Precedence can be overridden via ``gate_precedence`` dict with keys:
        - 'policy' (default: 80)
        - 'risk' (default: 60)
        - 'feedback' (default: 50)
        """
        policy_prec = self.gate_precedence.get('policy', PRECEDENCE_POLICY)
        risk_prec = self.gate_precedence.get('risk', PRECEDENCE_RISK)
        feedback_prec = self.gate_precedence.get('feedback', PRECEDENCE_FEEDBACK)

        gates: list[tuple[int, StrategicGate]] = [
            (policy_prec, self.strategic_gate),
            (risk_prec, RiskGate(self.risk_assessor, selector, self.risk_policy)),
        ]
        if self.feedback_gate is not None:
            gates.append((feedback_prec, HumanFeedbackGateWrapper(self.feedback_gate)))
        return CompositeStrategicGate(gates)

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

            if strategic_decision.decision == Decision.BLOCK:
                return self._record_block(
                    intent.owner_id, intent_record_id,
                    strategic_decision.reason or 'Blocked by strategic gate',
                    status='blocked',
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
            return ExecutionRecord(
                intent_record_id=intent_record_id,
                capability_record_id=selected_record_id,
                result_record_id=result_record_id,
                fault_record_id=None,
                status='ok' if result.ok else 'not_ok',
                notes=result.notes,
            )
        except CallerFault as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'caller_fault'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            raise exc
        except TaskFailure as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'task_failure'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            raise exc
        except SystemFault as exc:
            self.memory.record(
                owner_id=intent.owner_id,
                kind='fault',
                payload={'type': exc.__class__.__name__, 'message': str(exc), 'fault_class': 'system_fault'},
                provenance={'producer': 'ExecutiveMind', 'stage': 'fault'},
            )
            raise exc

    def _record_block(self, owner_id: str, intent_record_id: str, reason: str, status: str) -> ExecutionRecord:
        decision_record_id = self.memory.record(
            owner_id=owner_id,
            kind='strategic_decision',
            payload={'decision': 'block', 'reason': reason},
            provenance={'producer': 'ExecutiveMind', 'stage': 'strategic_gate'},
        )
        return ExecutionRecord(
            intent_record_id=intent_record_id,
            capability_record_id=None,
            result_record_id=None,
            fault_record_id=decision_record_id,
            status=status,
            notes=(reason,),
        )

    def _find_capability_by_name(self, name: str) -> Optional[CapabilityDossier]:
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
        primary_exception: Optional[Exception] = None  # The original error from the primary capability
        last_exception: Optional[Exception] = None

        for attempt in range(self.error_handler.effective_retry_policy.max_retries + 1):
            try:
                return capability.execute(intent, params)
            except (SystemFault, CallerFault) as exc:
                last_exception = exc
                if primary_exception is None:
                    primary_exception = exc
                break  # never retry these
            except TaskFailure as exc:
                last_exception = exc
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
        fallback_error: Optional[Exception] = None
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
            except Exception as exc:
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
            blob = ' '.join([dossier.name, dossier.signature, dossier.purpose]).lower()
            if goal and goal in blob:
                return dossier
        return dossiers[0]