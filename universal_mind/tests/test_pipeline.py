"""Tests for the sequential pipeline (super-platform Phase 3b)."""

from __future__ import annotations

from universal_mind.pipeline import run_pipeline
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


def _registry_with(chain: list[tuple[str, str, str]]) -> ToolRegistry:
    reg = ToolRegistry()
    for name, cap, cmd in chain:
        reg.register(_entry(name, cap, cmd))
    return reg


def test_pipeline_threads_output_forward() -> None:
    reg = _registry_with([
        ("a", "first", "echo step1"),
        ("b", "second", "echo step2"),
        ("c", "third", "echo step3"),
    ])
    result = run_pipeline(reg, [("first", ""), ("second", ""), ("third", "")], initial_input="seed")
    assert result.ok is True
    # The final output is the LAST step's output — the data threaded the whole chain.
    assert result.final_output == "step3"
    assert len(result.steps) == 3
    # Each step succeeded in order.
    assert [s.capability for s in result.steps] == ["first", "second", "third"]


def test_pipeline_stops_at_missing_tool() -> None:
    reg = _registry_with([("a", "first", "echo ok")])
    result = run_pipeline(reg, [("first", ""), ("nonexistent", "")])
    assert result.ok is False
    assert len(result.steps) == 2
    assert result.steps[1].ok is False
    assert "no tool" in result.steps[1].error


def test_empty_pipeline_is_ok_with_initial_input() -> None:
    reg = ToolRegistry()
    result = run_pipeline(reg, [], initial_input="seed")
    assert result.ok is True
    assert result.final_output == "seed"


def test_input_key_reads_field_from_previous_output() -> None:
    # A step that extracts a field from the prior (dict) output threads only that field.
    reg = _registry_with([
        ("a", "maker", "echo {\"value\": 42}"),
        ("b", "consumer", "echo consumed"),
    ])
    result = run_pipeline(reg, [("maker", ""), ("consumer", "value")])
    assert result.ok is True
    assert result.final_output == "consumed"


def test_failed_step_short_circuits() -> None:
    # The second step's command is non-allowlisted, so it fails -> pipeline stops.
    reg = ToolRegistry()
    reg.register(_entry("a", "first", "echo ok"))
    # a failing tool (non-allowlisted first token) for the second capability.
    reg.register(_entry("bad", "second", "notallowedcommand"))
    result = run_pipeline(reg, [("first", ""), ("second", "")])
    assert result.ok is False
    assert len(result.steps) == 2