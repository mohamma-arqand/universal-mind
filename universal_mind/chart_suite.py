"""ChartSuite — the full visualization toolbox, integrated (matplotlib).

The third integrated *program*: a complete charting engine — line, bar, pie,
histogram, scatter, multi-series — each producing a real image artifact. Reachable
as ONE capability set through the Connector protocol.

Fail-safe and isolated: outputs land in a temp dir (matplotlib Agg backend, no
display); failures return not-ok with the real error.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import matplotlib

from universal_mind.connectors import ConnectorResult

matplotlib.use("Agg")  # headless: real files, no display
from matplotlib import pyplot as plt


class ChartSuite:
    """The integrated matplotlib capability surface (a complete charting program)."""

    name = "chart-suite"
    capability = "chart"

    OPERATIONS = ("line", "bar", "pie", "histogram", "scatter")

    def _out_path(self, name: str, out_dir: str | None = None) -> Path:
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-chart-"))
        target.mkdir(parents=True, exist_ok=True)
        return target / name

    def _save(self, fig: Any, out_path: Path) -> dict[str, Any]:
        try:
            fig.savefig(out_path)
            plt.close(fig)
        except Exception as exc:  # noqa: BLE001 — real rendering errors surface
            return {"ok": False, "error": str(exc)}
        if not out_path.exists():
            return {"ok": False, "error": "chart was not produced"}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def line(self, series: dict[str, list[float]] | None = None, title: str = "Line chart") -> dict[str, Any]:
        data = series or {"a": [1, 3, 2, 5], "b": [2, 2, 4, 4]}
        fig, ax = plt.subplots()
        for label, values in data.items():
            ax.plot(values, label=label)
        ax.set_title(title)
        ax.legend()
        return self._save(fig, self._out_path("line.png"))

    def bar(self, categories: list[str] | None = None, values: list[float] | None = None, title: str = "Bar chart") -> dict[str, Any]:
        cats = categories or ["x", "y", "z"]
        vals = values or [3, 7, 5]
        fig, ax = plt.subplots()
        ax.bar(cats, vals)
        ax.set_title(title)
        return self._save(fig, self._out_path("bar.png"))

    def pie(self, values: list[float] | None = None, labels: list[str] | None = None, title: str = "Pie chart") -> dict[str, Any]:
        vals = values or [40, 35, 25]
        labs = labels or ["a", "b", "c"]
        fig, ax = plt.subplots()
        ax.pie(vals, labels=labs, autopct="%1.0f%%")
        ax.set_title(title)
        return self._save(fig, self._out_path("pie.png"))

    def histogram(self, data: list[float] | None = None, bins: int = 10, title: str = "Histogram") -> dict[str, Any]:
        values = data or [1, 2, 2, 3, 3, 3, 4, 4, 5]
        fig, ax = plt.subplots()
        ax.hist(values, bins=bins)
        ax.set_title(title)
        return self._save(fig, self._out_path("hist.png"))

    def scatter(self, xs: list[float] | None = None, ys: list[float] | None = None, title: str = "Scatter") -> dict[str, Any]:
        x = xs or [1, 2, 3, 4, 5]
        y = ys or [2, 4, 1, 8, 7]
        fig, ax = plt.subplots()
        ax.scatter(x, y)
        ax.set_title(title)
        return self._save(fig, self._out_path("scatter.png"))


class ChartSuiteConnector:
    """Adapter: ChartSuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: ChartSuite | None = None) -> None:
        self._suite = suite if suite is not None else ChartSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "line") or "line"
        method = {
            "line": lambda: self._suite.line(params.get("series"), params.get("title", "Line chart")),
            "bar": lambda: self._suite.bar(params.get("categories"), params.get("values")),
            "pie": lambda: self._suite.pie(params.get("values"), params.get("labels")),
            "histogram": lambda: self._suite.histogram(params.get("data")),
            "scatter": lambda: self._suite.scatter(params.get("xs"), params.get("ys")),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(
            ok=True,
            output={"path": result.get("path"), "bytes": result.get("bytes")},
        )


__all__ = ["ChartSuite", "ChartSuiteConnector"]