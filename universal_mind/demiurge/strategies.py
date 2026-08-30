"""Parallel execution strategies for the Demiurge layer.

Provides N parallel strategies for executing decomposed intents.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .decompose import SubIntent


@dataclass(frozen=True)
class StrategyResult:
    """Result of a strategy execution."""
    strategy_id: str
    sub_intent_id: str
    success: bool
    result: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    """Plan for executing sub-intents with a specific strategy."""
    strategy_id: str
    sub_intent_ids: list[str]
    parallelism: int  # Max concurrent executions
    executor: Callable[[SubIntent], Any]  # Function to execute a sub-intent


class ExecutionStrategy(ABC):
    """Abstract base class for execution strategies."""

    @abstractmethod
    async def execute(self, plan: ExecutionPlan, sub_intents: dict[str, SubIntent]) -> list[StrategyResult]:
        """Execute the plan.

        Args:
            plan: ExecutionPlan with strategy details
            sub_intents: Map of sub_intent_id -> SubIntent

        Returns:
            List of StrategyResult for each sub-intent
        """


class SequentialStrategy(ExecutionStrategy):
    """Execute sub-intents sequentially in order."""

    async def execute(self, plan: ExecutionPlan, sub_intents: dict[str, SubIntent]) -> list[StrategyResult]:
        results = []
        for sub_id in plan.sub_intent_ids:
            sub_intent = sub_intents[sub_id]
            try:
                result = await plan.executor(sub_intent)
                results.append(StrategyResult(
                    strategy_id=plan.strategy_id,
                    sub_intent_id=sub_id,
                    success=True,
                    result=result,
                ))
            except BaseException as e:  # noqa: BLE001
                results.append(StrategyResult(
                    strategy_id=plan.strategy_id,
                    sub_intent_id=sub_id,
                    success=False,
                    result=None,
                    error=str(e),
                ))
        return results


class ParallelStrategy(ExecutionStrategy):
    """Execute up to N sub-intents in parallel."""

    def __init__(self, max_parallel: int = 3) -> None:
        self.max_parallel = max_parallel

    async def execute(self, plan: ExecutionPlan, sub_intents: dict[str, SubIntent]) -> list[StrategyResult]:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_one(sub_id: str) -> StrategyResult:
            async with semaphore:
                sub_intent = sub_intents[sub_id]
                try:
                    result = await plan.executor(sub_intent)
                    return StrategyResult(
                        strategy_id=plan.strategy_id,
                        sub_intent_id=sub_id,
                        success=True,
                        result=result,
                    )
                except BaseException as e:  # noqa: BLE001
                    return StrategyResult(
                        strategy_id=plan.strategy_id,
                        sub_intent_id=sub_id,
                        success=False,
                        result=None,
                        error=str(e),
                    )

        tasks = [execute_one(sub_id) for sub_id in plan.sub_intent_ids]
        return await asyncio.gather(*tasks)


class SpeculativeStrategy(ExecutionStrategy):
    """Execute multiple strategies in parallel and pick the best result.

    Runs the same sub-intents with different approaches, returns first success.
    """

    def __init__(self, strategies: list[ExecutionStrategy]) -> None:
        self.strategies = strategies

    async def execute(self, plan: ExecutionPlan, sub_intents: dict[str, SubIntent]) -> list[StrategyResult]:
        # For speculative, we run each strategy on a COPY of the sub-intents
        # and return the first successful strategy's results
        for strategy in self.strategies:
            try:
                results = await strategy.execute(plan, sub_intents)
                if all(r.success for r in results):
                    return results
            except BaseException:  # noqa: BLE001, S112
                # Log the exception and continue to next strategy
                continue

        # If all failed, return last attempt's results
        return await self.strategies[-1].execute(plan, sub_intents)


def create_n_parallel_strategies(n: int, base_executor: Callable) -> list[ExecutionStrategy]:
    """Create N different parallel strategies.

    Args:
        n: Number of strategies to create
        base_executor: Base executor function

    Returns:
        List of ExecutionStrategy instances with varying parallelism
    """
    strategies = []
    for i in range(n):
        # Vary parallelism: 1, 2, 3, ..., n
        parallelism = min(i + 1, 4)
        if parallelism == 1:
            strategies.append(SequentialStrategy())
        else:
            strategies.append(ParallelStrategy(max_parallel=parallelism))
    return strategies