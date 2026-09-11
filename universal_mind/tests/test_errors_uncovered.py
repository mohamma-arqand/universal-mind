"""Coverage for core/errors.py's remaining branches."""

from __future__ import annotations

import pytest

from universal_mind.core.errors import (
    ErrorHandler,
    ErrorRecoveryStrategy,
    RetryPolicy,
    TaskFailure,
    retry_on_failure,
)


def test_get_fallback_returns_first_when_configured() -> None:
    handler = ErrorHandler(fallback_capability=["a", "b"], retry_policy=RetryPolicy(max_retries=0))
    assert handler.get_fallback() == ("a", {})


def test_get_fallback_none_when_not_configured() -> None:
    handler = ErrorHandler(retry_policy=RetryPolicy(max_retries=0))
    assert handler.get_fallback() is None


def test_error_recovery_strategy_defaults() -> None:
    s = ErrorRecoveryStrategy()
    assert s.on_failure(TaskFailure("x"), {}) is None
    assert s.can_recover(TaskFailure("x")) is False


def test_retry_on_failure_exhausts_and_reraises_last() -> None:
    """After retries are exhausted, the last exception is re-raised."""
    handler = ErrorHandler(
        retry_policy=RetryPolicy(max_retries=2, base_delay_seconds=0.0, jitter=False),
        sleep=lambda _d: None,
    )
    calls: list[int] = []

    @retry_on_failure(handler)
    def boom(_x: int) -> int:
        calls.append(1)
        raise TaskFailure("always fails")

    with pytest.raises(TaskFailure):
        boom(1)
    # the decorator loops range(max_retries=2) -> 2 calls total
    assert len(calls) == 2


def test_retry_on_failure_succeeds_after_transient_failures() -> None:
    handler = ErrorHandler(
        retry_policy=RetryPolicy(max_retries=3, base_delay_seconds=0.0, jitter=False),
        sleep=lambda _d: None,
    )
    state = {"n": 0}

    @retry_on_failure(handler)
    def flaky() -> int:
        state["n"] += 1
        if state["n"] < 3:
            raise TaskFailure("not yet")
        return 42

    assert flaky() == 42
    assert state["n"] == 3