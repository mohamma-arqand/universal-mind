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
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult



# Scratch dirs the platform creates under the system temp dir. Every one of
# them is disposable by construction; none of them was ever reaped, and during
# one 16-minute suite that left 124,000 directories and ~60 GB on disk (the
# live incident that made "No space left on device" the real gate).
_SCRATCH_PREFIXES = (
    "um-db-",
    "um-conn-",
    "um-chart-",
    "um-csv-",
    "um-img-",
    "um-excel-",
    "um_dashboard_",
)
_REAP_INTERVAL_S = 300.0  # at most one sweep every five minutes, per process
_REAP_MAX_AGE_S = 3600.0  # only scratch older than an hour: never a live suite
_last_reap = 0.0


def reap_stale_scratch(now: float | None = None, *, force: bool = False) -> int:
    """Delete scratch directories older than an hour. Returns how many went.

    Age-gated on purpose: a directory younger than the gate may belong to a
    suite another process is still using, and deleting it mid-run would be a
    silent data-loss bug. Throttled because the sweep walks the temp dir;
    ``force=True`` bypasses the throttle (tests and explicit maintenance).
    """
    global _last_reap
    import shutil as _shutil
    import time as _time

    stamp = _time.time() if now is None else now
    if not force and stamp - _last_reap < _REAP_INTERVAL_S:
        return 0
    _last_reap = stamp
    root = Path(tempfile.gettempdir())
    removed = 0
    for prefix in _SCRATCH_PREFIXES:
        try:
            entries = list(root.glob(prefix + "*"))
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
                if stamp - entry.stat().st_mtime < _REAP_MAX_AGE_S:
                    continue  # young: possibly live
                _shutil.rmtree(entry, ignore_errors=True)
                removed += 1
            except OSError:
                continue
    return removed


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
            # A throwaway scratch database: sweep the platform's older scratch
            # dirs while we are here (throttled internally) so a long test
            # session cannot bury the disk again.
            reap_stale_scratch()
            target = Path(tempfile.mkdtemp(prefix="um-db-")) / "mind.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(target)
        # Schemas this suite object has already built (see ensure_schema):
        # per-object on purpose, so a fresh suite always re-ensures.
        self._ensured: set[str] = set()
        # R39 HOT PATH: the persistent file is probed and validated ONCE per
        # process. The router's hot path (history + memory + learning) builds
        # ~10 suites per run; re-probing each time was half of every run's
        # wall time (~22ms each on Windows file I/O). Explicit db_path calls
        # (tests, rebuild flows) still validate every time — only the
        # shared, already-validated persistent file skips the re-probe.
        already_validated = persistent and type(self)._persistent_validated
        if not already_validated:
            # JOURNAL SAFETY: WAL is deliberately NOT enabled. In this platform's
            # real profile (tick + window + CLI opening the SAME file repeatedly
            # through fresh short-lived connections) WAL on a store whose header
            # was ever hand-rebuilt produced page corruption (the 2nd corruption
            # incident — root-caused, restored from the rotating backup). The
            # delete journal is atomic and matches the usage; the verified
            # rotating backup covers the residual risk.
            if target.exists():
                try:
                    import sqlite3 as _sq

                    probe = _sq.connect(str(target))
                    try:
                        probe.execute("PRAGMA journal_mode=DELETE")
                    finally:
                        probe.close()  # a leaked handle locks the file on Windows
                except _sq.Error:
                    pass
            # HEADER GUARD: a partially-overwritten db (an external writer once
            # splattered stderr over the header page) fails later with a cryptic
            # 'unsupported file format' deep inside sqlite3. Fail EARLY, with the
            # exact remedy, and never silently treat corruption as a schema issue.
            if target.exists() and target.stat().st_size >= 16:
                with open(target, "rb") as header_probe:
                    magic = header_probe.read(16)
                if magic != b"SQLite format 3\x00":
                    raise RuntimeError(
                        f"پایگاه داده خراب است (امضای فایل نامعتبر): {target} — "
                        "فایل را با scripts/rebuild_db.py بازسازی کن"
                    )
            if persistent:
                type(self)._persistent_validated = True

    # R39: one-time per-process validation flag for the persistent file.
    _persistent_validated: bool = False

    # R39: the persistent store is ONE file; building a fresh suite for it
    # (journal probe + header guard, ~22ms) on every hot-path call made half
    # of every run's wall time. The shared suite is stateless between calls
    # (each op opens/closes its own connection), so caching the WRAPPER is
    # safe for concurrent callers; the file itself is unchanged.
    _shared_persistent: dict[str, "DatabaseSuite"] = {}

    @classmethod
    def shared_persistent(cls) -> "DatabaseSuite":
        """The process-wide persistent suite (built once, reused hot)."""
        suite = cls._shared_persistent.get("main")
        if suite is None:
            suite = cls(persistent=True)
            cls._shared_persistent["main"] = suite
        return suite

    @property
    def db_path(self) -> str:
        """The real on-disk path of this database (auditable)."""
        return self._path

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """A genuinely-CLOSED connection per use: sqlite3's native context
        manager commits but never closes — on Windows every leaked handle
        locks the file (this suite's temp-dir cleanup caught it live)."""
        conn = sqlite3.connect(self._path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # R48-5 — THE READ POOL: one reusable read-only connection for the hot
    # path. The old open/close-per-query cost 17 fresh connections and
    # ~430ms per command; a single-threaded pooled reader removes the churn
    # WITHOUT touching the write path (insert/DDL keep the closed-handle
    # law that saved us from the Windows file-lock incidents). WAL stays
    # OFF by the project's journal-safety law; a pooled reader sees
    # committed data because every writer commits before returning.
    _read_pool: dict[str, sqlite3.Connection] = {}

    def _reader(self) -> sqlite3.Connection:
        """The pooled SELECT connection for this database path."""
        conn = type(self)._read_pool.get(self._path)
        if conn is None:
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            type(self)._read_pool[self._path] = conn
        return conn

    def close_reader(self) -> None:
        """Close this path's pooled reader (tests swap paths constantly)."""
        conn = type(self)._read_pool.pop(self._path, None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Many statements on ONE connection — the SAME closed-after-use law
        as ``_conn`` (no leaked handle can ever lock the file), but the hot
        writers stop paying one connect+commit PER STATEMENT. Measured live:
        a single simple run opened 27 connections; batching the hot writers
        collapses that to a handful, which is what keeps the run under the
        hot-path budget.
        """
        conn = sqlite3.connect(self._path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_many(self, statements: list[str]) -> dict[str, Any]:
        """Run several DDL/DML statements in ONE transaction."""
        if not statements:
            return {"ok": False, "error": "no statements"}
        try:
            with self.transaction() as conn:
                for sql in statements:
                    conn.execute(sql)
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "executed": len(statements), "error": ""}

    def ensure_schema(self, name: str, statements: list[str]) -> bool:
        """Run this DDL once per SUITE OBJECT — returns True if it ran.

        Measured live: the hot writers re-ran their CREATE TABLE / CREATE INDEX
        on every construction and even on every call, each re-run costing a
        full connect+commit. The guard is per object on purpose: a fresh
        DatabaseSuite always re-ensures, so a database file that was deleted
        and recreated gets its schema back — no stale memo can ever leave a
        real file bare (a file-identity memo looked tempting and was WRONG:
        NTFS reuses file indexes, so a recreated database was skipped).
        A long-lived suite (``shared_persistent``) is where the saving lives.
        """
        if name in self._ensured:
            return False
        self.execute_many(statements)
        self._ensured.add(name)
        return True

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

    def query(self, sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any]:
        """Run a real SELECT and return real rows as dicts.

        ``params`` are bound safely (never formatted into the SQL string);
        None keeps the historical no-parameter behavior unchanged.
        """
        if not sql.strip().lower().startswith("select"):
            return {"ok": False, "error": "query must be a SELECT"}
        try:
            # R48-5 — SELECTs ride the pooled reader (no fresh connection,
            # no per-query open/close churn). A broken pool falls back to
            # the closed-handle path — a reader is a lens, never a blocker.
            try:
                conn = self._reader()
                cursor = conn.execute(sql, params) if params else conn.execute(sql)
                rows = [dict(r) for r in cursor.fetchall()]
            except sqlite3.Error:
                # a stale/broken pooled reader: drop it and answer from the
                # closed-handle path — the pool is a lens, never a blocker.
                self.close_reader()
                with self._conn() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(sql, params) if params else conn.execute(sql)
                    rows = [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "rows": rows, "count": len(rows), "error": ""}

    def tables(self) -> dict[str, Any]:
        """List the real tables that exist in this database."""
        try:
            conn = self._reader()
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
        # A params["persistent"]=True call rebinds to the FIXED on-disk database
        # (~/.universal-mind/mind.db) so stored data survives the session —
        # both for INSERTS (the operator said store) and QUERIES (reading back
        # what was stored must hit the same persistent store, not an empty temp).
        if params.get("persistent") and operation in ("insert_many", "query", "execute", "tables"):
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