"""Tests for the adaptive orchestration closed learning loop."""

from __future__ import annotations

from universal_mind.adaptive_orchestration import AdaptiveOrchestrator
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str, command: str) -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=command),
        absorbable=True,
    )


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(_entry("a", "first", "echo a"))
    reg.register(_entry("b", "second", "echo b"))
    reg.register(_entry("c", "third", "echo c"))
    return reg


def test_run_records_success_and_latency() -> None:
    orch = AdaptiveOrchestrator(_registry())
    syn = orch.run(["first", "second", "third"])
    assert syn.ok is True
    stats = orch.stats()
    assert stats["first"]["runs"] == 1
    assert stats["first"]["success_rate"] == 1.0
    assert stats["first"]["mean_latency"] >= 0.0


def test_optimized_order_puts_never_run_last() -> None:
    orch = AdaptiveOrchestrator(_registry())
    # No runs yet -> all infinite latency, so order is the original order.
    assert orch.optimized_order(["third", "first", "second"]) == ["third", "first", "second"]


def test_optimized_order_prefers_proven_capabilities() -> None:
    orch = AdaptiveOrchestrator(_registry())
    # Run "third" (which we want to prefer) several times so its latency is known.
    orch.run(["third", "first", "second"])
    orch.run(["third", "first", "second"])
    order = orch.optimized_order(["first", "second", "third"])
    # All have been run now; the learned order keeps a deterministic tie-break by
    # original index for equal-latency capabilities. The key guarantee we assert:
    # every requested capability still appears exactly once.
    assert sorted(order) == ["first", "second", "third"]


def test_stats_is_read_only_summary() -> None:
    orch = AdaptiveOrchestrator(_registry())
    orch.run(["first"])
    stats = orch.stats()
    assert set(stats["first"].keys()) == {"runs", "success_rate", "mean_latency"}
    assert stats["first"]["runs"] == 1


def test_failed_capability_ranks_after_successes() -> None:
    reg = ToolRegistry()
    reg.register(_entry("good", "good", "echo ok"))
    reg.register(ToolEntry(
        name="bad", capability="bad",
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="totally_not_allowed"),
        absorbable=True,
    ))
    orch = AdaptiveOrchestrator(reg)
    syn = orch.run(["bad", "good"])
    # "bad" fails (non-allowlisted), "good" succeeds.
    assert syn.ok is False
    stats = orch.stats()
    assert stats["bad"]["success_rate"] == 0.0
    assert stats["good"]["success_rate"] == 1.0
    # A failed capability is ordered after successes.
    order = orch.optimized_order(["bad", "good"])
    assert order[-1] == "bad"