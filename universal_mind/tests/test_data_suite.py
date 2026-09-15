"""Tests for the integrated DataSuite (full numpy capability surface)."""

from __future__ import annotations

from typing import Any
from universal_mind.data_suite import DataSuite, DataSuiteConnector


def test_stats_real_descriptive_numbers() -> None:
    suite = DataSuite()
    out = suite.stats([2, 4, 4, 4, 5, 5, 7, 9])
    assert out["ok"] is True
    s = out["stats"]
    assert s["mean"] == 5.0
    assert s["count"] == 8
    assert s["min"] == 2.0 and s["max"] == 9.0
    assert s["median"] == 4.5


def test_matrix_multiply_real() -> None:
    suite = DataSuite()
    out = suite.matrix_multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]])
    assert out["ok"] is True
    assert out["result"] == [[19.0, 22.0], [43.0, 50.0]]


def test_solve_real_linear_system() -> None:
    suite = DataSuite()
    # 2x + y = 5; x + 3y = 10  ->  x = 1, y = 3
    out = suite.solve([[2, 1], [1, 3]], [5, 10])
    assert out["ok"] is True
    assert abs(out["solution"][0] - 1.0) < 1e-9
    assert abs(out["solution"][1] - 3.0) < 1e-9


def test_determinant_and_eigenvalues_real() -> None:
    suite = DataSuite()
    det = suite.determinant([[4, 7], [2, 6]])
    assert det["ok"] is True
    assert abs(det["determinant"] - 10.0) < 1e-9
    eig = suite.eigenvalues([[2, 0], [0, 3]])
    assert eig["ok"] is True
    assert sorted(eig["eigenvalues"]) == [2.0, 3.0]


def test_normalize_real() -> None:
    suite = DataSuite()
    out = suite.normalize([0, 5, 10])
    assert out["ok"] is True
    assert out["normalized"] == [0.0, 0.5, 1.0]


def test_correlate_real() -> None:
    suite = DataSuite()
    out = suite.correlate([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert out["ok"] is True
    assert abs(out["correlation"] - 1.0) < 1e-9  # perfect positive correlation


def test_full_surface_all_operations_real() -> None:
    """Every one of the suite's 23 declared operations performs REAL numeric work
    (the full numpy surface, not a subset)."""
    suite = DataSuite()
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]
    matrix = [[4, 7], [2, 6]]
    inputs: dict[str, dict[str, Any]] = {
        "stats": {"data": x},
        "variance": {"data": x},
        "percentile": {"data": x, "q": 50},
        "cumulative_sum": {"data": x},
        "differences": {"data": x},
        "unique_values": {"data": [1, 1, 2, 3]},
        "argmax": {"data": x},
        "argmin": {"data": x},
        "histogram_counts": {"data": x, "bins": 2},
        "rounded": {"data": [1.567], "decimals": 1},
        "matrix_multiply": {"a": [[1, 2], [3, 4]], "b": [[1, 0], [0, 1]]},
        "solve": {"coefficients": [[2, 1], [1, 3]], "constants": [5, 10]},
        "determinant": {"matrix": matrix},
        "eigenvalues": {"matrix": [[2, 0], [0, 3]]},
        "inverse": {"matrix": [[2, 0], [0, 2]]},
        "dot_product": {"a": [1, 2], "b": [3, 4]},
        "svd_rank": {"matrix": [[1, 2], [3, 4]]},
        "correlate": {"a": x, "b": y},
        "covariance": {"a": x, "b": y},
        "polyfit": {"xs": [1, 2, 3], "ys": [2, 4, 6], "degree": 1},
        "fourier": {"data": x},
        "clip_range": {"data": [1, 5, 20], "low": 0, "high": 10},
        "normalize": {"data": x},
    }
    conn = DataSuiteConnector()
    ok, failed = 0, []
    for op in suite.OPERATIONS:
        result = conn.connect({}, {"operation": op, **inputs.get(op, {})})
        if result.ok is True:
            ok += 1
        else:
            failed.append((op, result.error[:60]))
    assert ok == len(suite.OPERATIONS), f"{ok}/{len(suite.OPERATIONS)} real; failures: {failed}"


def test_polyfit_real_regression() -> None:
    suite = DataSuite()
    out = suite.polyfit([1, 2, 3], [2, 4, 6], 1)
    assert out["ok"] is True
    # slope 2, intercept ~0
    assert abs(out["coefficients"][0] - 2.0) < 1e-9


def test_fourier_real_spectrum() -> None:
    suite = DataSuite()
    out = suite.fourier([1, 2, 3, 4])
    assert out["ok"] is True
    assert len(out["magnitudes"]) == 4


def test_singular_system_fails_clean() -> None:
    suite = DataSuite()
    out = suite.solve([[1, 2], [2, 4]], [1, 2])  # singular
    assert out["ok"] is False


def test_constant_series_correlation_fails_clean() -> None:
    suite = DataSuite()
    out = suite.correlate([1, 1, 1], [1, 2, 3])
    assert out["ok"] is False
    assert "undefined" in out["error"]


def test_connector_dispatches_operations() -> None:
    conn = DataSuiteConnector()
    stats = conn.connect({}, {"operation": "stats", "data": [1, 2, 3]})
    assert stats.ok is True and stats.output["mean"] == 2.0
    solve = conn.connect({}, {"operation": "solve", "coefficients": [[1, 0], [0, 1]], "constants": [3, 4]})
    assert solve.ok is True and solve.output["solution"] == [3.0, 4.0]


def test_unknown_operation_fails_clean() -> None:
    conn = DataSuiteConnector()
    result = conn.connect({}, {"operation": "teleport"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_data_suite_joins_the_synthesis_loop() -> None:
    """The whole numeric program participates in the multi-tool synthesis loop.

    'data' is an officially registered real capability — the loop works without
    mutating the shared connector table (the earlier mutate-then-delete pattern
    here caused real cross-test contamination in the full suite)."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(name="data", capability="data",
                           connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                           absorbable=True))
    syn = orchestrate(reg, ["data"], connector_factory=real_connector_factory)
    assert syn.ok is True
    # The no-params call computes real stats over the default series.
    stats = syn.output["synthesized_from"]["data"]
    assert stats["mean"] == 5.0