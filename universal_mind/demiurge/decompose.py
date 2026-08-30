"""Intent decomposition for the Demiurge layer.

Breaks a high-level intent into smaller, executable sub-intents.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.intent import Intent, IntentIncomplete


@dataclass(frozen=True)
class SubIntent:
    """A decomposed sub-intent with ordering constraints."""
    id: str
    goal: str
    success_criteria: list[str]
    constraints: list[str]
    depends_on: tuple[str, ...]  # IDs of sub-intents that must complete first
    estimated_cost: float
    priority: int  # Lower = higher priority


@dataclass(frozen=True)
class DecompositionResult:
    """Result of intent decomposition."""
    original_intent: Intent
    sub_intents: list[SubIntent]
    execution_order: list[str]  # Topologically sorted IDs


class DecompositionError(IntentIncomplete):
    """Raised when intent cannot be decomposed."""


def decompose_intent(intent: Intent, max_depth: int = 3) -> DecompositionResult:
    """Decompose an intent into ordered sub-intents.

    Uses simple heuristic decomposition based on goal structure.
    Real implementations would use LLM or planning algorithms.

    Args:
        intent: The intent to decompose
        max_depth: Maximum decomposition depth

    Returns:
        DecompositionResult with sub-intents and execution order
    """
    # Simple heuristic: split by "and", ",", or sequential indicators
    goal = intent.goal.lower()

    # Identify sub-goals
    sub_goals = []
    if ' and ' in goal:
        sub_goals = [g.strip() for g in goal.split(' and ')]
    elif ', ' in goal:
        sub_goals = [g.strip() for g in goal.split(', ')]
    elif ' then ' in goal:
        sub_goals = [g.strip() for g in goal.split(' then ')]
    else:
        # Single goal - return as-is
        sub_goals = [intent.goal]

    # Limit depth
    sub_goals = sub_goals[:max_depth]

    # Create sub-intents
    sub_intents = []
    for i, sg in enumerate(sub_goals):
        sub_id = f"{intent.id}_sub{i}"
        sub_intents.append(SubIntent(
            id=sub_id,
            goal=sg,
            success_criteria=[f"Complete: {sg}"],
            constraints=[],
            depends_on=tuple(f"{intent.id}_sub{j}" for j in range(i)),
            estimated_cost=10.0 + i * 5.0,
            priority=i,
        ))

    # Topological sort (already in order due to depends_on)
    execution_order = [si.id for si in sub_intents]

    return DecompositionResult(
        original_intent=intent,
        sub_intents=sub_intents,
        execution_order=execution_order,
    )