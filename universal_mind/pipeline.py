"""Sequential pipeline — orchestrated synthesis where output A feeds input B (Phase 3b).

Phase 3a (in :mod:`universal_mind.orchestration`) runs tools in parallel and fuses
their outputs structurally. Phase 3b is the *sequential* kind: a chain where each
tool's output becomes the next tool's input — the "data flows through many hands"
form of synthesis that no amount of parallel concatenation can produce.

The pipeline is declared as an ordered list of (capability, input-key) steps. Each
step reaches the best tool for its capability, passes the *previous* step's output
forward as the input for the next, and so the final output is the result of the
whole chain, not a bundle of independent results. A step that fails (no tool, or a
failed connect) stops the chain and marks the pipeline failed — a broken link is
never papered over with a partial result.

Deterministic and local; the data threading is explicit via a declared ``input_key``
so the pipeline is auditable (which field of a tool's output fed the next tool).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.connectors import connector_for
from universal_mind.tool_registry import ToolRegistry


class PipelineError(Exception):
    """Raised when a pipeline step cannot be honored or fails mid-chain."""


@dataclass(frozen=True)
class PipelineStepResult:
    """One step's outcome in the chain."""

    capability: str
    tool_name: str
    output: Any
    ok: bool
    error: str = ""


@dataclass(frozen=True)
class PipelineResult:
    """The terminal result of a sequential pipeline."""

    final_output: Any
    steps: tuple[PipelineStepResult, ...]
    ok: bool                  # True only when every step succeeded to the end


def run_pipeline(
    registry: ToolRegistry,
    steps: list[tuple[str, str]],
    *,
    initial_input: Any = None,
) -> PipelineResult:
    """Run an ordered chain where each tool's output becomes the next tool's input.

    ``steps`` is a list of ``(capability, input_key)`` pairs. ``input_key`` is the
    field of the *previous* step's output to thread forward as the current step's
    input parameter (or ``""`` to pass the whole previous output verbatim). The
    first step receives ``initial_input``. The chain stops at the first failure.

    Returns the final step's output plus the per-step trail.
    """
    if not steps:
        return PipelineResult(final_output=initial_input, steps=(), ok=True)

    results: list[PipelineStepResult] = []
    current_input: Any = initial_input

    for capability, input_key in steps:
        tool = registry.best_for(capability)
        if tool is None:
            results.append(
                PipelineStepResult(capability, "", None, False, f"no tool can honor '{capability}'")
            )
            return PipelineResult(final_output=None, steps=tuple(results), ok=False)

        # Thread the previous output forward as this step's input parameter.
        params: dict[str, Any] = {"input": current_input}
        if input_key:
            params = {"input": _field(current_input, input_key)}

        result = connector_for(tool.connection_mechanism).connect(tool.connection, params)
        results.append(
            PipelineStepResult(capability, tool.name, result.output, result.ok, result.error)
        )
        if not result.ok:
            return PipelineResult(final_output=None, steps=tuple(results), ok=False)

        current_input = result.output

    return PipelineResult(final_output=current_input, steps=tuple(results), ok=True)


def _field(value: Any, key: str) -> Any:
    """Read ``key`` from a mapping (or return the value unchanged if not a mapping)."""
    if isinstance(value, dict) and key in value:
        return value[key]
    return value


__all__ = ["PipelineError", "PipelineResult", "PipelineStepResult", "run_pipeline"]