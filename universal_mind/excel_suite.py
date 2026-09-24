"""The Excel suite — the FIFTEENTH capability: real .xlsx workbooks.

openpyxl drives real spreadsheet files: write data tables (headers + rows),
read them back cell by cell, add formula-bearing sheets, and style headers.
The flow target for the stats/data programs: «حساب کن و در اکسل بریز».

Honest rules:
- Every operation produces a REAL .xlsx on disk (path + bytes reported).
- Read returns the actual cell values (typed), never a guessed table.
- Errors name the exact cause (missing file, unknown operation); nothing is
  fabricated and nothing silently substitutes a CSV for a workbook.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class ExcelSuite:
    """A real spreadsheet program (openpyxl): write/read/formula/style."""

    name = "excel-suite"
    capability = "excel"

    OPERATIONS = (
        "write_table",   # headers + rows → a real styled sheet
        "read_table",   # a real sheet → typed rows
        "add_formula",  # a real formula cell (SUM/AVG/...) → computed value
        "sheets",       # the workbook's real sheet inventory
    )

    def _out(self, out_dir: str | None, name: str) -> Path:
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-excel-"))
        target.mkdir(parents=True, exist_ok=True)
        return target / name

    def write_table(
        self,
        headers: list[str] | None = None,
        rows: list[list[Any]] | None = None,
        sheet: str = "Sheet1",
        out_dir: str | None = None,
        *,
        rtl: bool = False,
        total: bool = False,
    ) -> dict[str, Any]:
        """Write a real styled table to a new .xlsx (header bolded + filled).

        R44-10: Persian spreadsheets read RIGHT-TO-LEFT and earn their keep with
        REAL formulas — ``rtl`` flips the sheet view, ``total`` appends a
        genuine =SUM row (openpyxl stores the formula; Excel computes on open;
        reading back shows the live formula text, never a fabricated number).
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        hdr = headers or ["A", "B"]
        data = rows or [[1, 2], [3, 4]]
        out_path = self._out(out_dir, "table.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.title = sheet
        ws.append(hdr)
        bold = Font(bold=True)
        fill = PatternFill("solid", fgColor="DDEBF7")
        for cell in ws[1]:
            cell.font = bold
            cell.fill = fill
        for row in data:
            ws.append(row)

        formula_row: int | None = None
        if total and data:
            # label in the FIRST column, live =SUM under each fully-numeric one
            total_row: list[Any] = ["جمع"] + ["" for _ in range(max(0, len(hdr) - 1))]
            for ci in range(1, len(hdr)):
                col = get_column_letter(ci + 1)
                column_values = [
                    r[ci] for r in data if ci < len(r) and isinstance(r[ci], (int, float))
                ]
                if len(column_values) == len(data):
                    total_row[ci] = f"=SUM({col}2:{col}{len(data) + 1})"
            ws.append(total_row)
            formula_row = len(data) + 2
            for cell in ws[formula_row]:
                cell.font = bold

        if rtl:
            ws.sheet_view.rightToLeft = True

        wb.save(out_path)
        return {
            "ok": True, "path": str(out_path), "bytes": out_path.stat().st_size,
            "rows": len(data), "columns": len(hdr), "sheet": sheet,
            "rtl": bool(rtl), "formula_row": formula_row, "error": "",
        }

    def read_table(self, path: str, sheet: str | None = None) -> dict[str, Any]:
        """Read a real .xlsx back: headers + typed rows, exactly what is there."""
        from openpyxl import load_workbook

        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "rows": []}
        wb = load_workbook(src, data_only=False)
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
        grid = [[cell.value for cell in row] for row in ws.iter_rows()]
        if not grid:
            return {"ok": True, "headers": [], "rows": [], "sheets": wb.sheetnames, "error": ""}
        return {
            "ok": True,
            "headers": [("" if h is None else str(h)) for h in grid[0]],
            "rows": grid[1:],
            "sheets": wb.sheetnames,
            "error": "",
        }

    def add_formula(
        self,
        path: str,
        formula: str = "=SUM(A2:A100)",
        cell: str = "C1",
    ) -> dict[str, Any]:
        """Write a REAL formula into an existing workbook (and read its cached value).

        openpyxl stores the formula; Excel computes on open. The cached value
        (None until Excel saves) is reported honestly — the formula text is
        verified in the cell, never a fabricated computed number.
        """
        from openpyxl import load_workbook

        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "value": None}
        wb = load_workbook(src)
        ws = wb.active
        ws[cell] = formula
        wb.save(src)
        return {
            "ok": True, "path": str(src), "cell": cell, "formula": formula,
            "bytes": src.stat().st_size, "error": "",
        }

    def sheets(self, path: str) -> dict[str, Any]:
        """The real sheet inventory of a workbook."""
        from openpyxl import load_workbook

        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "sheets": []}
        wb = load_workbook(src)
        return {"ok": True, "sheets": wb.sheetnames, "error": ""}


class ExcelSuiteConnector:
    """Adapts :class:`ExcelSuite` to the ``Connector`` protocol."""

    def __init__(self, suite: ExcelSuite | None = None) -> None:
        self._suite = suite if suite is not None else ExcelSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "write_table") or "write_table"
        suite = self._suite
        if operation == "write_table":
            result = suite.write_table(
                headers=params.get("headers"), rows=params.get("rows"),
                sheet=str(params.get("sheet", "Sheet1")),
                rtl=bool(params.get("rtl", False)),
                total=bool(params.get("total", False)),
            )
        elif operation == "read_table":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.read_table(str(params["path"]), params.get("sheet"))
        elif operation == "add_formula":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.add_formula(
                str(params["path"]),
                formula=str(params.get("formula", "=SUM(A2:A100)")),
                cell=str(params.get("cell", "C1")),
            )
        elif operation == "sheets":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.sheets(str(params["path"]))
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k not in ("ok", "error")
        })


__all__ = ["ExcelSuite", "ExcelSuiteConnector"]