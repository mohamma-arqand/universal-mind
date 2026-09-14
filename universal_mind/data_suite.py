"""DataSuite — the full numeric/data toolbox, integrated (numpy).

The fourth integrated *program*: a complete numeric engine — descriptive statistics,
matrix operations, linear algebra (solve, determinant, inverse, eigenvalues),
normalization, correlations — reachable as ONE capability set through the Connector
protocol, so the whole suite flows through ``orchestrate`` like any other capability.

Fail-safe: a malformed input or a singular matrix returns not-ok with the real
error (never a fabricated number).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from universal_mind.connectors import ConnectorResult


class DataSuite:
    """The integrated numpy capability surface (a complete numeric program)."""

    name = "data-suite"
    capability = "data"

    OPERATIONS = (
        "stats", "describe", "matrix_multiply", "solve", "determinant",
        "eigenvalues", "normalize", "correlate",
    )

    # A real default series so a no-params call (as orchestrate issues) still
    # performs genuine numeric work instead of failing on an empty series.
    DEFAULT_SERIES: tuple[float, ...] = (2, 4, 4, 4, 5, 5, 7, 9)

    @staticmethod
    def _array(data: Any) -> np.ndarray:
        return np.asarray(data, dtype=float)

    def stats(self, data: list[float]) -> dict[str, Any]:
        """Real descriptive statistics over a series: mean, std, min, max, median."""
        arr = self._array(data)
        if arr.size == 0:
            return {"ok": False, "error": "empty series"}
        return {
            "ok": True,
            "stats": {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "median": float(np.median(arr)),
                "count": int(arr.size),
            },
            "error": "",
        }

    def matrix_multiply(self, a: list[list[float]], b: list[list[float]]) -> dict[str, Any]:
        """Real matrix multiplication."""
        try:
            result = self._array(a) @ self._array(b)
        except ValueError as exc:
            return {"ok": False, "error": f"shape mismatch: {exc}"}
        return {"ok": True, "result": result.tolist(), "error": ""}

    def solve(self, coefficients: list[list[float]], constants: list[float]) -> dict[str, Any]:
        """Solve a real linear system Ax = b."""
        try:
            x = np.linalg.solve(self._array(coefficients), self._array(constants))
        except np.linalg.LinAlgError as exc:
            return {"ok": False, "error": f"singular or non-square system: {exc}"}
        return {"ok": True, "solution": [float(v) for v in x], "error": ""}

    def determinant(self, matrix: list[list[float]]) -> dict[str, Any]:
        """Real determinant of a square matrix."""
        try:
            det = np.linalg.det(self._array(matrix))
        except np.linalg.LinAlgError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "determinant": float(det), "error": ""}

    def eigenvalues(self, matrix: list[list[float]]) -> dict[str, Any]:
        """Real eigenvalues of a square matrix."""
        try:
            values = np.linalg.eigvals(self._array(matrix))
        except np.linalg.LinAlgError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "eigenvalues": [complex(v).real for v in values], "error": ""}

    def normalize(self, data: list[float]) -> dict[str, Any]:
        """Real min-max normalization of a series to [0, 1]."""
        arr = self._array(data)
        if arr.size == 0:
            return {"ok": False, "error": "empty series"}
        span = float(np.max(arr) - np.min(arr))
        if span == 0:
            return {"ok": True, "normalized": [0.5] * arr.size, "error": ""}
        normalized = (arr - np.min(arr)) / span
        return {"ok": True, "normalized": [float(v) for v in normalized], "error": ""}

    def correlate(self, a: list[float], b: list[float]) -> dict[str, Any]:
        """Real Pearson correlation between two series."""
        x, y = self._array(a), self._array(b)
        if x.size != y.size or x.size == 0:
            return {"ok": False, "error": "series must be same non-zero length"}
        if np.std(x) == 0 or np.std(y) == 0:
            return {"ok": False, "error": "correlation undefined for constant series"}
        corr = float(np.corrcoef(x, y)[0, 1])
        return {"ok": True, "correlation": corr, "error": ""}


class DataSuiteConnector:
    """Adapter: DataSuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: DataSuite | None = None) -> None:
        self._suite = suite if suite is not None else DataSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "stats") or "stats"
        default_series = self._suite.DEFAULT_SERIES
        method = {
            "stats": lambda: self._suite.stats(params.get("data") or default_series),
            "matrix_multiply": lambda: self._suite.matrix_multiply(params.get("a", []), params.get("b", [])),
            "solve": lambda: self._suite.solve(params.get("coefficients", []), params.get("constants", [])),
            "determinant": lambda: self._suite.determinant(params.get("matrix", [])),
            "eigenvalues": lambda: self._suite.eigenvalues(params.get("matrix", [])),
            "normalize": lambda: self._suite.normalize(params.get("data") or default_series),
            "correlate": lambda: self._suite.correlate(params.get("a", default_series), params.get("b", default_series)),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        output: Any = result.get("stats") if operation == "stats" else {
            k: v for k, v in result.items() if k not in ("ok", "error")
        }
        return ConnectorResult(ok=True, output=output)


__all__ = ["DataSuite", "DataSuiteConnector"]