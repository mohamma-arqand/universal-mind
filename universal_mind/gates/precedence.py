"""PrecedencePipeline: deterministic gate evaluation with full trace.

GATE_PRECEDENCE is a frozen module constant. It is not configurable by env var,
config key, or constructor kwarg. This is fixed policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from .base import Gate, GateResult, Verdict, combine_verdicts

# Type for gate identifiers
GateId = str

# Fixed gate precedence order — not configurable.
# Higher in the list = higher precedence = runs first.
# PowerZero veto is terminal: once vetoed, no downstream gate may re-admit.
GATE_PRECEDENCE: Final[tuple[GateId, ...]] = (
    "PowerZero",      # 1000 - absolute veto authority
    "Layering",       # 900  - layer boundary enforcement
    "Policy",         # 800  - strategic policy decisions
    "Risk",           # 600  - risk assessment
    "HumanFeedback",  # 400  - historical rejection
)


def resolve_order() -> tuple[GateId, ...]:
    """Return the frozen gate precedence order.

    This is the single source of truth for gate evaluation order.
    No parameters, no overrides, no configuration.
    """
    return GATE_PRECEDENCE


@dataclass(frozen=True)
class PipelineJudgment:
    """Complete result of pipeline evaluation."""
    decision: Verdict
    trace: list[GateResult]

    @property
    def allowed(self) -> bool:
        return self.decision == Verdict.ALLOW

    @property
    def deferred(self) -> bool:
        return self.decision == Verdict.DEFER

    @property
    def denied(self) -> bool:
        return self.decision == Verdict.DENY


class PrecedencePipeline:
    """
    Deterministic gate evaluation pipeline with frozen precedence.

    Ordering: by GATE_PRECEDENCE module constant — order is fixed policy.
    Gates not in GATE_PRECEDENCE are rejected at construction time.

    Short-circuit: any gate returning DENY stops evaluation immediately.
    Skipped gates are recorded in trace with skipped=True.

    Veto: The gate with highest precedence that returns DENY acts as
    an absolute veto — nothing after it runs, nothing can override.
    PowerZero veto is terminal: once vetoed, no downstream gate may re-admit.
    """

    def __init__(self, gates: list[Gate]):
        # Build a precedence map from the frozen module constant
        precedence_map = {name: i for i, name in enumerate(GATE_PRECEDENCE)}

        # Validate all gates have names in GATE_PRECEDENCE
        for gate in gates:
            if gate.name not in precedence_map:
                raise ValueError(
                    f"Gate '{gate.name}' not in GATE_PRECEDENCE. "
                    f"Valid names: {list(GATE_PRECEDENCE)}"
                )

        # Sort by GATE_PRECEDENCE order (lower index = higher precedence)
        self.gates = sorted(gates, key=lambda g: precedence_map[g.name])

        # Verify unique names
        names = [g.name for g in self.gates]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate gate names: {names}")

    def evaluate(self, context: dict[str, Any]) -> PipelineJudgment:
        """Evaluate all gates in precedence order.

        Returns PipelineJudgment with:
        - decision: final combined verdict
        - trace: list of GateResult for every gate (including skipped)
        """
        trace: list[GateResult] = []
        verdicts: list[Verdict] = []
        vetoed = False

        for i, gate in enumerate(self.gates):
            # Check if we should short-circuit (after a DENY was already added to verdicts)
            if vetoed:
                # This gate is skipped due to earlier DENY
                trace.append(GateResult(
                    gate_name=gate.name,
                    precedence=i,  # Position in GATE_PRECEDENCE
                    verdict=Verdict.DENY,
                    reason="Skipped: earlier gate returned DENY",
                    skipped=True,
                    skip_reason="hard veto by earlier gate",
                ))
                continue

            # Evaluate the gate
            verdict = gate.evaluate(context)
            trace.append(GateResult(
                gate_name=gate.name,
                precedence=i,
                verdict=verdict,
                reason=f"Evaluated: {verdict.value}",
                skipped=False,
            ))
            verdicts.append(verdict)

            # Hard short-circuit on DENY - but still record skipped for remaining gates
            if verdict == Verdict.DENY:
                vetoed = True

        # Combine verdicts (only from gates that actually ran)
        decision = combine_verdicts(verdicts)

        return PipelineJudgment(decision=decision, trace=trace)


def create_default_pipeline(
    power_zero: Gate,
    risk_gate: Gate | None,
    strategic_gate: Gate,
    human_feedback_gate: Gate | None = None,
    layering_gate: Gate | None = None,
) -> PrecedencePipeline:
    """Create a pipeline with standard gates using frozen GATE_PRECEDENCE.

    Gate order is determined by GATE_PRECEDENCE module constant:
    - PowerZero: 1000 (absolute veto authority)
    - Layering: 900 (layer boundary enforcement)
    - Policy: 800 (strategic policy decisions)
    - Risk: 600 (risk assessment)
    - HumanFeedback: 400 (historical rejection)

    Gates must have correct names matching GATE_PRECEDENCE entries.
    """
    from .layering import create_layering_gate

    gates = [power_zero]

    # Layering is always included - create default if not provided
    if layering_gate is not None:
        gates.append(layering_gate)
    else:
        gates.append(create_layering_gate())

    gates.append(strategic_gate)

    if risk_gate is not None:
        gates.append(risk_gate)

    if human_feedback_gate is not None:
        gates.append(human_feedback_gate)

    return PrecedencePipeline(gates)