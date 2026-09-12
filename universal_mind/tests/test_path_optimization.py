"""Tests for path optimization (super-platform Phase 4)."""

from __future__ import annotations

from universal_mind.path_optimization import learn_path
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str) -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command=name),
        absorbable=True,
    )


def test_learn_path_picks_champion_by_evidence() -> None:
    reg = ToolRegistry()
    proven = _entry("proven", "edit_image")
    proven.record_evidence(True, 1.0)
    rookie = _entry("rookie", "edit_image")
    rookie.record_evidence(True, 0.3)
    reg.register(rookie)
    reg.register(proven)
    plan = learn_path(reg)
    champ = next(c for c in plan.champions if c.capability == "edit_image")
    assert champ.tool_name == "proven"
    assert champ.mean_score == 1.0


def test_route_orders_reliable_capabilities_first() -> None:
    reg = ToolRegistry()
    strong = _entry("s", "strong")
    strong.record_evidence(True, 0.9)
    weak = _entry("w", "weak")
    weak.record_evidence(False, 0.0)
    reg.register(strong)
    reg.register(weak)
    plan = learn_path(reg)
    assert plan.route[0] == "strong"   # higher reliability first
    assert plan.route[1] == "weak"


def test_capability_with_no_tool_is_absent() -> None:
    reg = ToolRegistry()
    reg.register(_entry("a", "only"))
    plan = learn_path(reg)
    assert [c.capability for c in plan.champions] == ["only"]


def test_no_evidence_champion_ranks_last() -> None:
    reg = ToolRegistry()
    proven = _entry("proven", "p")
    proven.record_evidence(True, 0.8)
    untested = _entry("untested", "u")
    reg.register(untested)
    reg.register(proven)
    plan = learn_path(reg)
    assert plan.route[0] == "p"   # proven outranks untested
    assert plan.route[1] == "u"