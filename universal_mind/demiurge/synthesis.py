"""Result synthesis for the Demiurge layer.

Merges results from parallel strategy executions into a unified result.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .strategies import StrategyResult


@dataclass(frozen=True)
class SynthesisResult:
    """Result of synthesizing multiple strategy results."""
    success: bool
    merged_result: Any
    strategy_results: list[StrategyResult]
    synthesis_method: str
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0


class SynthesisError(Exception):
    """Raised when synthesis fails."""


def synthesize_results(
    strategy_results: list[StrategyResult],
    method: str = 'first_success',
    merge_fn: Callable[..., Any] | None = None
) -> SynthesisResult:
    """Synthesize results from multiple strategy executions.

    Args:
        strategy_results: List of StrategyResult from different strategies
        method: Synthesis method ('first_success', 'majority_vote', 'merge_all', 'custom')
        merge_fn: Custom merge function for 'custom' method

    Returns:
        SynthesisResult with merged outcome
    """
    if not strategy_results:
        return SynthesisResult(
            success=False,
            merged_result=None,
            strategy_results=[],
            synthesis_method=method,
            confidence=0.0,
        )

    successful = [r for r in strategy_results if r.success]

    if method == 'first_success':
        if successful:
            first = successful[0]
            return SynthesisResult(
                success=True,
                merged_result=first.result,
                strategy_results=strategy_results,
                synthesis_method=method,
                confidence=0.8,  # Lower confidence since we didn't verify others
            )
        else:
            # All failed - return first failure
            first = strategy_results[0]
            return SynthesisResult(
                success=False,
                merged_result=None,
                strategy_results=strategy_results,
                synthesis_method=method,
                conflicts=[{'error': first.error, 'sub_intent_id': first.sub_intent_id}],
                confidence=0.0,
            )

    elif method == 'majority_vote':
        # Group by result (for comparable results)
        result_counts: dict[str, int] = {}
        for r in successful:
            key = str(r.result)
            result_counts[key] = result_counts.get(key, 0) + 1

        if result_counts:
            # Find majority
            max_count = max(result_counts.values())
            majority_result = max(result_counts, key=lambda k: result_counts[k])
            confidence = max_count / len(strategy_results)
            return SynthesisResult(
                success=True,
                merged_result=majority_result,
                strategy_results=strategy_results,
                synthesis_method=method,
                confidence=confidence,
            )
        else:
            first = strategy_results[0]
            return SynthesisResult(
                success=False,
                merged_result=None,
                strategy_results=strategy_results,
                synthesis_method=method,
                conflicts=[{'error': first.error, 'sub_intent_id': first.sub_intent_id}],
                confidence=0.0,
            )

    elif method == 'merge_all':
        if merge_fn is None:
            # Default: combine into list
            merged = [r.result for r in successful]
        else:
            merged = merge_fn([r.result for r in successful])

        return SynthesisResult(
            success=len(successful) > 0,
            merged_result=merged,
            strategy_results=strategy_results,
            synthesis_method=method,
            confidence=1.0 if successful else 0.0,
        )

    elif method == 'custom' and merge_fn is not None:
        merged = merge_fn(strategy_results)
        return SynthesisResult(
            success=True,
            merged_result=merged,
            strategy_results=strategy_results,
            synthesis_method=method,
            confidence=1.0,
        )

    else:
        raise SynthesisError(f"Unknown synthesis method: {method}")


def synthesize_by_sub_intent(
    results_by_sub_intent: dict[str, list[StrategyResult]],
    method: str = 'first_success',
) -> dict[str, SynthesisResult]:
    """Synthesize results grouped by sub-intent.

    Args:
        results_by_sub_intent: Map of sub_intent_id -> list of StrategyResult
        method: Synthesis method

    Returns:
        Map of sub_intent_id -> SynthesisResult
    """
    return {
        sub_id: synthesize_results(results, method)
        for sub_id, results in results_by_sub_intent.items()
    }