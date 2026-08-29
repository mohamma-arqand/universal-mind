"""Error taxonomy and handling for telemetry layer."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, TypeVar
from functools import wraps
import time
import random


class Disposition(str, Enum):
    """Error disposition determines retry behavior and throttle impact."""
    RETRYABLE = 'retryable'      # Transient/system errors - retry with backoff
    NON_RETRYABLE = 'non_retryable'  # Caller faults - fail fast, no throttle impact
    FATAL = 'fatal'              # System corruption - never retry, alert immediately


class UniversalMindError(Exception):
    """Base class for all package-specific exceptions."""
    
    disposition: Disposition = Disposition.NON_RETRYABLE
    fault_class: str = 'unknown'


class TransientError(UniversalMindError):
    """Raised for transient/system failures that may succeed on retry.
    
    These include network timeouts, temporary resource unavailability, etc.
    They are retryable and count toward the error-rate throttle.
    """
    disposition = Disposition.RETRYABLE
    fault_class = 'transient'


class PermanentError(UniversalMindError):
    """Raised for permanent/task failures that won't succeed on retry without intervention.
    
    These are retryable (may be transient on next attempt) and count toward throttle.
    """
    disposition = Disposition.RETRYABLE
    fault_class = 'permanent'


class PolicyViolation(UniversalMindError):
    """Raised when an operation violates a configured policy (rate limit, quota, etc.).
    
    These are NOT retryable by default and count toward throttle.
    """
    disposition = Disposition.NON_RETRYABLE
    fault_class = 'policy_violation'


class ContractBreach(UniversalMindError):
    """Raised when a caller violates a contract (invalid input, schema mismatch, etc.).
    
    These are NON-RETRYABLE and explicitly EXCLUDED from error-rate throttling.
    They represent caller faults, not system failures.
    """
    disposition = Disposition.NON_RETRYABLE
    fault_class = 'contract_breach'


class FatalError(UniversalMindError):
    """Raised for fatal system corruption that requires immediate intervention.
    
    Never retry. Alert immediately.
    """
    disposition = Disposition.FATAL
    fault_class = 'fatal'


# Legacy aliases for backward compatibility
SystemFault = TransientError
TaskFailure = PermanentError
CallerFault = ContractBreach


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
    
    retry_policy: Optional[RetryPolicy] = None
    #: Capability name, or ordered list of names, tried in order when the primary
    #: capability's retries are exhausted. An empty/None value disables fallback.
    fallback_capability: Optional[str | list[str]] = None
    fallback_params: Optional[dict[str, Any]] = None
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
        """Determine if we should retry based on attempt count and exception disposition."""
        if attempt >= self.effective_retry_policy.max_retries:
            return False
        # Never retry on NON_RETRYABLE or FATAL errors
        if isinstance(exception, UniversalMindError):
            if exception.disposition != Disposition.RETRYABLE:
                return False
        # Only retry TaskFailure/PermanentError and TransientError by default
        if not isinstance(exception, (TransientError, PermanentError)):
            return False
        return True

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

    def get_fallback(self) -> Optional[tuple[str, dict[str, Any]]]:
        """Return the first fallback capability (name, params) if configured."""
        chain = self.get_fallback_chain()
        return chain[0] if chain else None


class ErrorRecoveryStrategy:
    """Strategy for recovering from execution failures."""
    
    def on_failure(self, exception: Exception, context: dict[str, Any]) -> Optional[str]:
        """Called when an execution fails. Returns fallback capability name or None."""
        return None
    
    def can_recover(self, exception: Exception) -> bool:
        """Determine if this strategy can handle the given exception."""
        return False


F = TypeVar('F', bound=Callable[..., Any])


def retry_on_failure(handler: ErrorHandler, attempts: Optional[int] = None) -> Callable[[F], F]:
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
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if not handler.should_retry(attempt, e):
                        raise e
                    delay = handler.effective_retry_policy.get_delay(attempt)
                    if delay > 0:
                        handler.sleep(delay)
            
            # All retries exhausted
            assert last_exception is not None
            raise last_exception from last_exception
        
        return wrapper  # type: ignore[return-value]
    return decorator