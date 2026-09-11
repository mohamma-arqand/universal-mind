"""Exception hierarchies for system faults and task failures."""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


class UniversalMindError(Exception):
    """Base class for all package-specific exceptions."""


class SystemFault(UniversalMindError):
    """Raised when the system body or invariants are broken."""


class TaskFailure(UniversalMindError):
    """Raised when a task fails but the system remains healthy."""


class CallerFault(UniversalMindError):
    """Raised when the caller provides invalid input (non-retryable, not a system fault).
    
    This includes contract violations, validation errors, and other caller-side issues.
    These are NOT retried and do NOT count toward error-rate throttling.
    """


@dataclass(frozen=True)
class RetryPolicy:
    """Configurable retry policy with exponential backoff and jitter.

    Defaults provide a safe, production-friendly configuration:
    - Exponential backoff: base_delay * (2 ** attempt)
    - Full jitter: random value in [0, delay]
    - Maximum delay cap to prevent excessive waits

    Tests can inject a zero-delay policy or fake sleep function.
    """
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter: bool = True  # full jitter: random.uniform(0, delay)
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt (0-indexed)."""
        delay = self.base_delay_seconds * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay_seconds)
        if self.jitter:
            delay = random.uniform(0, delay)
        return delay


@dataclass
class ErrorHandler:
    """Configuration for error handling and fallback behavior."""

    retry_policy: RetryPolicy | None = None
    #: Capability name, or ordered list of names, tried in order when the primary
    #: capability's retries are exhausted. An empty/None value disables fallback.
    fallback_capability: str | list[str] | None = None
    fallback_params: dict[str, Any] | None = None
    #: Callable used to pause between retries; injectable so tests can provide a
    #: fake/instant no-op delay instead of a real ``time.sleep``.
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()

    @property
    def effective_retry_policy(self) -> RetryPolicy:
        """Return the retry policy, guaranteed non-None after __post_init__."""
        assert self.retry_policy is not None
        return self.retry_policy

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if we should retry based on attempt count and exception type."""
        if attempt >= self.effective_retry_policy.max_retries:
            return False
        # Never retry on system faults or caller faults.
        if isinstance(exception, (SystemFault, CallerFault)):
            return False
        return isinstance(exception, TaskFailure)

    def get_fallback_chain(self) -> list[tuple[str, dict[str, Any]]]:
        """Return the ordered fallback chain as (name, params) pairs.

        Accepts a single capability name (backwards compatible) or a list of
        names representing a fallback chain.
        """
        if not self.fallback_capability:
            return []
        names = (
            [self.fallback_capability]
            if isinstance(self.fallback_capability, str)
            else list(self.fallback_capability)
        )
        return [(name, self.fallback_params or {}) for name in names]

    def get_fallback(self) -> tuple[str, dict[str, Any]] | None:
        """Return the first fallback capability (name, params) if configured."""
        chain = self.get_fallback_chain()
        return chain[0] if chain else None


class ErrorRecoveryStrategy:
    """Strategy for recovering from execution failures."""
    
    def on_failure(self, exception: Exception, context: dict[str, Any]) -> str | None:
        """Called when an execution fails. Returns fallback capability name or None."""
        return None
    
    def can_recover(self, exception: Exception) -> bool:
        """Determine if this strategy can handle the given exception."""
        return False


def retry_on_failure(handler: ErrorHandler, attempts: int | None = None) -> Callable[[F], F]:
    """Decorator for retrying a function on failure.
    
    Args:
        handler: ErrorHandler configuration
        attempts: Override max_retries if specified
        
    Returns:
        Decorated function that retries on failure
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            max_retries = attempts if attempts is not None else handler.effective_retry_policy.max_retries
            last_exception: Exception | None = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if not handler.should_retry(attempt, e):
                        raise
                    delay = handler.effective_retry_policy.get_delay(attempt)
                    if delay > 0:
                        handler.sleep(delay)
            
            # All retries exhausted. If max_retries was 0, the loop never ran
            # and we cannot re-raise a captured exception; that is a caller
            # misconfiguration, surfaced explicitly rather than an opaque
            # 'raise None'.
            if last_exception is None:
                raise RuntimeError("retry_on_failure exhausted with no exception captured (max_retries=0?)")
            raise last_exception
        
        return wrapper  # type: ignore[return-value]
    return decorator
