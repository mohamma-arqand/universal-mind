"""DAG and cycle detection for execution graphs.

Provides topological sorting and cycle detection for sub-intent dependencies.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GraphNode:
    """Node in the execution DAG."""
    id: str
    data: Any
    dependencies: tuple[str, ...]  # Node IDs this node depends on


@dataclass(frozen=True)
class TopologicalSortResult:
    """Result of topological sorting."""
    sorted_nodes: list[str]
    has_cycles: bool
    cycles: list[list[str]]  # List of cycles found (empty if none)


class CycleDetected(Exception):
    """Raised when a cycle is detected in the dependency graph."""
    def __init__(self, cycles: list[list[str]]) -> None:
        self.cycles = cycles
        super().__init__(f"Cycle detected in dependency graph: {cycles}")


class ExecutionGraph:
    """Directed acyclic graph for execution ordering."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        for dep in node.dependencies:
            self._adjacency[dep].add(node.id)
            self._reverse_adjacency[node.id].add(dep)

    def topological_sort(self) -> TopologicalSortResult:
        """Perform topological sort using Kahn's algorithm.

        Returns:
            TopologicalSortResult with sorted node IDs and cycle info
        """
        # Compute in-degrees
        in_degree = {node_id: len(self._reverse_adjacency[node_id]) for node_id in self._nodes}

        # Queue nodes with no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

        sorted_order = []
        while queue:
            node_id = queue.popleft()
            sorted_order.append(node_id)

            # Decrease in-degree of neighbors
            for neighbor in self._adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        has_cycles = len(sorted_order) != len(self._nodes)
        cycles = []

        if has_cycles:
            cycles = self._find_cycles()

        return TopologicalSortResult(
            sorted_nodes=sorted_order,
            has_cycles=has_cycles,
            cycles=cycles,
        )

    def _find_cycles(self) -> list[list[str]]:
        """Find cycles using DFS."""
        visited = set()
        rec_stack = set()
        path = []
        cycles = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle - extract it
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)
            path.pop()

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_dependents(self, node_id: str) -> set[str]:
        """Get nodes that depend on the given node."""
        return self._adjacency.get(node_id, set())

    def get_dependencies(self, node_id: str) -> set[str]:
        """Get nodes the given node depends on."""
        return self._reverse_adjacency.get(node_id, set())


def build_graph_from_sub_intents(sub_intents: list[Any]) -> ExecutionGraph:
    """Build an execution graph from sub-intents.

    Args:
        sub_intents: List of SubIntent objects

    Returns:
        ExecutionGraph with nodes and dependencies
    """
    graph = ExecutionGraph()
    for si in sub_intents:
        node = GraphNode(
            id=si.id,
            data=si,
            dependencies=si.depends_on,
        )
        graph.add_node(node)
    return graph