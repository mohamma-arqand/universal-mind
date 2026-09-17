"""The CSV suite — the NINETEENTH capability: real delimited files.

Python's csv module (stdlib) reads and writes REAL .csv files — the universal
interchange format. Persian headers round-trip (utf-8-sig so Excel opens
them correctly); typing is honored on read (numbers come back as numbers).

Honest rules:
- Every operation produces or reads a REAL file (path + bytes reported).
- Read returns exactly the rows that are there — a header-only file is
  header-only; an empty file says so. Nothing is inferred or padded.
- Encoding is utf-8-sig on write (the BOM Excel needs) and tolerant on read
  (utf-8-sig falls back to plain utf-8).
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class CsvSuite:
    """A real CSV program: write/read typed rows with Persian-safe encoding."""

    name = "csv-suite"
    capability = "csv"

    OPERATIONS = ("write_table", "read_table")

    def _out(self, out_dir: str | None, name: str) -> Path:
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-csv-"))
        target.mkdir(parents=True, exist_ok=True)
        return target / name

    def write_table(
        self,
        headers: list[str] | None = None,
        rows: list[list[Any]] | None = None,
        out_dir: str | None = None,
    ) -> dict[str, Any]:
        """Write a real .csv (utf-8-sig — Excel opens Persian headers as-is)."""
        hdr = headers or ["a", "b"]
        data = rows or [[1, 2], [3, 4]]
        out_path = self._out(out_dir, "table.csv")
        try:
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(hdr)
                for row in data:
                    writer.writerow(row)
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": "", "bytes": 0}
        return {
            "ok": True, "path": str(out_path), "bytes": out_path.stat().st_size,
            "rows": len(data), "columns": len(hdr), "error": "",
        }

    def read_table(self, path: str) -> dict[str, Any]:
        """Read a real .csv back: headers + typed rows (numbers stay numbers)."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "headers": [], "rows": []}
        try:
            with open(src, encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                try:
                    headers = next(reader)
                except StopIteration:
                    return {"ok": True, "headers": [], "rows": [], "empty": True, "error": ""}
                typed_rows: list[list[Any]] = []
                for raw in reader:
                    typed_rows.append([self._typed(cell) for cell in raw])
        except (OSError, csv.Error) as exc:
            return {"ok": False, "error": str(exc), "headers": [], "rows": []}
        return {
            "ok": True, "headers": headers, "rows": typed_rows,
            "empty": not typed_rows, "error": "",
        }

    @staticmethod
    def _typed(cell: str) -> Any:
        """A cell that parses as a number IS a number; otherwise the string."""
        try:
            as_int = int(cell)
            return as_int
        except ValueError:
            pass
        try:
            as_float = float(cell)
            return as_float
        except ValueError:
            return cell


class CsvSuiteConnector:
    """Adapts :class:`CsvSuite` to the ``Connector`` protocol."""

    def __init__(self, suite: CsvSuite | None = None) -> None:
        self._suite = suite if suite is not None else CsvSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "write_table") or "write_table"
        suite = self._suite
        if operation == "write_table":
            result = suite.write_table(
                headers=params.get("headers"), rows=params.get("rows"),
            )
        elif operation == "read_table":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.read_table(str(params["path"]))
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k not in ("ok", "error")
        })


__all__ = ["CsvSuite", "CsvSuiteConnector"]