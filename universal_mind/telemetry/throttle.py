"""Execution throttle for concurrency and error-rate limiting."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExecutionThrottle:
    """Throttle execution based on concurrency and error-rate policy."""

    max_concurrent: int = 10
    error_rate_threshold: float = 0.1

    def should_allow(self, recent_errors: int, recent_executions: int, caller_faults: int = 0) -> bool:
        """Determine whether execution should proceed under throttle policy.

        Caller faults (invalid input, contract violations) are excluded from the
        error-rate calculation: they are not system failures and must not trip the
        throttle. Only ``TransientError``/``PermanentError`` records count as errors.
        """
        if recent_executions >= self.max_concurrent:
            return False
        effective_errors = max(0, recent_errors - caller_faults)
        error_rate = effective_errors / max(recent_executions, 1)
        return error_rate <= self.error_rate_threshold


class ThrottlePolicy(Protocol):
    """Protocol for custom throttle policies."""
    
    def should_allow(self, recent_errors: int, recent_executions: int, caller_faults: int = 0) -> bool:
        ...