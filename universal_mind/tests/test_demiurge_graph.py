"""Tests for the execution DAG (topological sort + cycle detection)."""

from __future__ import annotations

from universal_mind.demiurge.decompose import SubIntent
from universal_mind.demiurge.graph import (
    CycleDetected,
    ExecutionGraph,
    GraphNode,
    build_graph_from_sub_intents,
)


def _node(node_id: str, deps: tuple[str, ...] = ()) -> GraphNode:
    return GraphNode(id=node_id, data={"id": node_id}, dependencies=deps)


def test_topological_sort_linear_chain() -> None:
    g = ExecutionGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b", ("a",)))
    g.add_node(_node("c", ("b",)))
    result = g.topological_sort()
    assert not result.has_cycles
    assert result.cycles == []
    assert result.sorted_nodes == ["a", "b", "c"]


def test_topological_sort_respects_dependencies() -> None:
    g = ExecutionGraph()
    g.add_node(_node("b", ("a",)))
    g.add_node(_node("a"))
    result = g.topological_sort()
    assert result.sorted_nodes.index("a") < result.sorted_nodes.index("b")


def test_topological_sort_detects_cycle() -> None:
    g = ExecutionGraph()
    g.add_node(_node("a", ("b",)))
    g.add_node(_node("b", ("a",)))
    result = g.topological_sort()
    assert result.has_cycles
    assert result.cycles  # a non-empty cycle list


def test_cycle_detected_exception_carries_cycles() -> None:
    exc = CycleDetected([["a", "b", "a"]])
    assert exc.cycles == [["a", "b", "a"]]
    assert "Cycle detected" in str(exc)


def test_get_node_returns_none_for_missing() -> None:
    g = ExecutionGraph()
    g.add_node(_node("a"))
    assert g.get_node("a") is not None
    assert g.get_node("missing") is None


def test_get_dependents_and_dependencies() -> None:
    g = ExecutionGraph()
    g.add_node(_node("b", ("a",)))
    assert g.get_dependencies("b") == {"a"}
    assert g.get_dependents("a") == {"b"}
    assert g.get_dependents("z") == set()
    assert g.get_dependencies("z") == set()


def test_build_graph_from_sub_intents() -> None:
    si = [
        SubIntent("s0", "g0", ["c"], [], (), 1.0, 0),
        SubIntent("s1", "g1", ["c"], [], ("s0",), 1.0, 1),
    ]
    g = build_graph_from_sub_intents(si)
    assert g.get_node("s0") is not None
    assert g.get_dependencies("s1") == {"s0"}
    result = g.topological_sort()
    assert result.sorted_nodes == ["s0", "s1"]


def test_topological_sort_multiple_roots() -> None:
    g = ExecutionGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    g.add_node(_node("c", ("a", "b")))
    result = g.topological_sort()
    assert set(result.sorted_nodes) == {"a", "b", "c"}
    assert result.sorted_nodes.index("c") > result.sorted_nodes.index("a")
    assert result.sorted_nodes.index("c") > result.sorted_nodes.index("b")