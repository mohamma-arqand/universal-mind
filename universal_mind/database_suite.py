"""DatabaseSuite — the full SQL toolbox, integrated (SQLite, stdlib).

The fifth integrated *program*: a complete relational database engine — table
creation, inserts, queries with WHERE/ORDER/aggregate, updates, deletes — reachable
as ONE capability set through the Connector protocol.

Persistence is real (a SQLite file on disk in a temp dir), so data survives across
calls within a suite instance. Fail-safe: a SQL error returns not-ok with the real
database error, never a fabricated row.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class DatabaseSuite:
    """The integrated sqlite3 capability surface (a complete SQL program)."""

    name = "db-suite"
    capability = "database"

    OPERATIONS = ("execute", "query", "insert_many", "tables")

    DEFAULT_DB_DIR = Path.home() / ".universal-mind"

    def __init__(self, db_path: str | None = None, *, persistent: bool = False) -> None:
        """A real SQLite database.

        ``persistent=True`` binds the suite to a FIXED on-disk database
        (``~/.universal-mind/mind.db``) that survives across sessions — the
        operator's accumulated data is kept, not discarded with the temp dir.
        The default remains a throwaway temp db (tests/isolation stay safe).
        """
        if db_path:
            target = Path(db_path)
        elif persistent:
            target = self.DEFAULT_DB_DIR / "mind.db"
        else:
            target = Path(tempfile.mkdtemp(prefix="um-db-")) / "mind.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(target)

    @property
    def db_path(self) -> str:
        """The real on-disk path of this database (auditable)."""
        return self._path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def execute(self, sql: str) -> dict[str, Any]:
        """Execute a DDL/DML statement (CREATE/INSERT/UPDATE/DELETE) for real."""
        if not sql.strip():
            return {"ok": False, "error": "empty SQL"}
        try:
            with self._conn() as conn:
                conn.execute(sql)
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "executed": sql.strip()[:120], "error": ""}

    def insert_many(self, table: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Insert real rows (list of column->value dicts) into a table."""
        if not rows:
            return {"ok": False, "error": "no rows"}
        first = rows[0]
        columns = list(first.keys())
        if any(list(r.keys()) != columns for r in rows):
            return {"ok": False, "error": "all rows must share the same columns"}
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        try:
            with self._conn() as conn:
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(c + ' TEXT' for c in columns)})")
                conn.executemany(sql, [[r[c] for c in columns] for r in rows])
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "inserted": len(rows), "error": ""}

    def query(self, sql: str) -> dict[str, Any]:
        """Run a real SELECT and return real rows as dicts."""
        if not sql.strip().lower().startswith("select"):
            return {"ok": False, "error": "query must be a SELECT"}
        try:
            with self._conn() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql)
                rows = [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "rows": rows, "count": len(rows), "error": ""}

    def tables(self) -> dict[str, Any]:
        """List the real tables that exist in this database."""
        try:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                names = [r[0] for r in cursor.fetchall()]
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "tables": names, "error": ""}


class DatabaseSuiteConnector:
    """Adapter: DatabaseSuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: DatabaseSuite | None = None) -> None:
        self._suite = suite if suite is not None else DatabaseSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "query") or "query"
        # A params["persistent"]=True insert rebinds this call to the FIXED
        # on-disk database (~/.universal-mind/mind.db) so the stored data
        # survives the session — the operator said store; it must last.
        if params.get("persistent") and operation == "insert_many":
            self._suite = DatabaseSuite(persistent=True)
        # A missing SQL defaults to a real, harmless catalog query, so a no-params
        # call (as orchestrate issues) still performs genuine database work.
        default_sql = "SELECT name, type FROM sqlite_master WHERE type='table'"
        sql = params.get("sql") or default_sql
        method = {
            "execute": lambda: self._suite.execute(sql),
            "query": lambda: self._suite.query(sql),
            "insert_many": lambda: self._suite.insert_many(params.get("table", ""), params.get("rows", [])),
            "tables": lambda: self._suite.tables(),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        output: Any = result.get("rows") if operation == "query" else {
            k: v for k, v in result.items() if k not in ("ok", "error")
        }
        if operation == "insert_many":
            output["db_path"] = self._suite.db_path  # auditable: where the data lives
        return ConnectorResult(ok=True, output=output)


__all__ = ["DatabaseSuite", "DatabaseSuiteConnector"]