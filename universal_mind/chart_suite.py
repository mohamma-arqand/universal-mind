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


def _apply_persian_font() -> None:
    """Point matplotlib at a Persian-capable OS font (Segoe UI/Tahoma shape and
    bidi Arabic-script glyphs themselves; the default DejaVu draws boxes)."""
    from matplotlib import font_manager

    names = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Segoe UI", "Tahoma", "Arial"):
        if candidate in names:
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break


def _has_persian(*texts: object) -> bool:
    """True when any of the texts carries Arabic-script (Persian) characters."""
    for t in texts:
        if isinstance(t, str) and any("\u0600" <= ch <= "\u06FF" for ch in t):
            return True
    return False


class ChartSuite:
    """The integrated matplotlib capability surface (a complete charting program)."""

    name = "chart-suite"
    capability = "chart"

    OPERATIONS = (
        "line", "bar", "barh", "pie", "histogram", "hist2d", "scatter",
        "boxplot", "violin", "stackplot", "step", "contour", "errorbar",
        "fill_between",
    )

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
        if _has_persian(title, *data.keys()):
            _apply_persian_font()
        fig, ax = plt.subplots()
        for label, values in data.items():
            ax.plot(values, label=label)
        ax.set_title(title)
        ax.legend()
        return self._save(fig, self._out_path("line.png"))

    def bar(self, categories: list[str] | None = None, values: list[float] | None = None, title: str = "Bar chart") -> dict[str, Any]:
        cats = categories or ["x", "y", "z"]
        vals = values or [3, 7, 5]
        if _has_persian(title, *cats):
            _apply_persian_font()
        fig, ax = plt.subplots()
        ax.bar(cats, vals)
        ax.set_title(title)
        return self._save(fig, self._out_path("bar.png"))

    def pie(self, values: list[float] | None = None, labels: list[str] | None = None, title: str = "Pie chart") -> dict[str, Any]:
        vals = values or [40, 35, 25]
        labs = labels or ["a", "b", "c"]
        if _has_persian(title, *labs):
            _apply_persian_font()
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

    # --- extended chart surface (real matplotlib) ---
    def barh(self, categories: list[str] | None = None, values: list[float] | None = None, title: str = "Horizontal bar") -> dict[str, Any]:
        cats = categories or ["x", "y", "z"]
        vals = values or [3, 7, 5]
        fig, ax = plt.subplots()
        ax.barh(cats, vals)
        ax.set_title(title)
        return self._save(fig, self._out_path("barh.png"))

    def boxplot(self, data: list[list[float]] | None = None, labels: list[str] | None = None, title: str = "Boxplot") -> dict[str, Any]:
        groups = data or [[1, 2, 3, 4, 5], [2, 3, 4, 5, 6]]
        fig, ax = plt.subplots()
        ax.boxplot(groups, tick_labels=labels or [f"g{i+1}" for i in range(len(groups))])
        ax.set_title(title)
        return self._save(fig, self._out_path("boxplot.png"))

    def violin(self, data: list[list[float]] | None = None, labels: list[str] | None = None, title: str = "Violin") -> dict[str, Any]:
        groups = data or [[1, 2, 3, 4, 5], [2, 3, 4, 5, 6]]
        fig, ax = plt.subplots()
        ax.violinplot(groups, showmedians=True)
        ax.set_xticks(range(1, len(groups) + 1))
        ax.set_xticklabels(labels or [f"g{i+1}" for i in range(len(groups))])
        ax.set_title(title)
        return self._save(fig, self._out_path("violin.png"))

    def stackplot(self, series: dict[str, list[float]] | None = None, title: str = "Stacked area") -> dict[str, Any]:
        data = series or {"a": [1, 2, 3], "b": [2, 1, 2], "c": [1, 1, 1]}
        labels = list(data.keys())
        fig, ax = plt.subplots()
        ax.stackplot(range(len(next(iter(data.values())))), *data.values(), labels=labels)
        ax.legend(loc="upper left")
        ax.set_title(title)
        return self._save(fig, self._out_path("stackplot.png"))

    def step(self, series: dict[str, list[float]] | None = None, title: str = "Step chart") -> dict[str, Any]:
        data = series or {"a": [1, 3, 2, 5]}
        fig, ax = plt.subplots()
        for label, values in data.items():
            ax.step(range(len(values)), values, label=label, where="mid")
        ax.legend()
        ax.set_title(title)
        return self._save(fig, self._out_path("step.png"))

    def hist2d(self, xs: list[float] | None = None, ys: list[float] | None = None, title: str = "2D histogram") -> dict[str, Any]:
        x = xs or [1, 2, 2, 3, 3, 3, 4, 4, 5]
        y = ys or [1, 1, 2, 2, 3, 3, 4, 4, 5]
        fig, ax = plt.subplots()
        ax.hist2d(x, y, bins=10, cmap="viridis")
        ax.set_title(title)
        return self._save(fig, self._out_path("hist2d.png"))

    def contour(self, title: str = "Contour") -> dict[str, Any]:
        import numpy as np

        x = np.linspace(-3, 3, 60)
        y = np.linspace(-3, 3, 60)
        xs, ys = np.meshgrid(x, y)
        zs = np.exp(-(xs**2 + ys**2) / 2)
        fig, ax = plt.subplots()
        cs = ax.contourf(xs, ys, zs, levels=20, cmap="viridis")
        fig.colorbar(cs, ax=ax)
        ax.set_title(title)
        return self._save(fig, self._out_path("contour.png"))

    def errorbar(self, xs: list[float] | None = None, ys: list[float] | None = None, err: list[float] | None = None, title: str = "Error bars") -> dict[str, Any]:
        x = xs or [1, 2, 3, 4, 5]
        y = ys or [2, 4, 1, 8, 7]
        e = err or [0.3, 0.4, 0.2, 0.8, 0.5]
        fig, ax = plt.subplots()
        ax.errorbar(x, y, yerr=e, fmt="o", capsize=4)
        ax.set_title(title)
        return self._save(fig, self._out_path("errorbar.png"))

    def fill_between(self, xs: list[float] | None = None, lower: list[float] | None = None, upper: list[float] | None = None, title: str = "Filled band") -> dict[str, Any]:
        x = xs or [1, 2, 3, 4, 5]
        lo = lower or [1, 2, 1.5, 3, 2.5]
        hi = upper or [2, 3, 2.5, 4, 3.5]
        fig, ax = plt.subplots()
        ax.fill_between(x, lo, hi, alpha=0.4)
        ax.plot(x, [(a + b) / 2 for a, b in zip(lo, hi, strict=False)], label="mean")  # paired bands
        ax.legend()
        ax.set_title(title)
        return self._save(fig, self._out_path("fill_between.png"))


class ChartSuiteConnector:
    """Adapter: ChartSuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: ChartSuite | None = None) -> None:
        self._suite = suite if suite is not None else ChartSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "line") or "line"
        method = {
            "line": lambda: self._suite.line(params.get("series"), params.get("title", "Line chart")),
            "bar": lambda: self._suite.bar(params.get("categories"), params.get("values")),
            "barh": lambda: self._suite.barh(params.get("categories"), params.get("values")),
            "pie": lambda: self._suite.pie(params.get("values"), params.get("labels")),
            "histogram": lambda: self._suite.histogram(params.get("data")),
            "hist2d": lambda: self._suite.hist2d(params.get("xs"), params.get("ys")),
            "scatter": lambda: self._suite.scatter(params.get("xs"), params.get("ys")),
            "boxplot": lambda: self._suite.boxplot(params.get("data"), params.get("labels")),
            "violin": lambda: self._suite.violin(params.get("data"), params.get("labels")),
            "stackplot": lambda: self._suite.stackplot(params.get("series")),
            "step": lambda: self._suite.step(params.get("series")),
            "contour": lambda: self._suite.contour(params.get("title", "Contour")),
            "errorbar": lambda: self._suite.errorbar(params.get("xs"), params.get("ys"), params.get("err")),
            "fill_between": lambda: self._suite.fill_between(params.get("xs"), params.get("lower"), params.get("upper")),
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