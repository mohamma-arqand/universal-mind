"""Tests for the integrated DatabaseSuite (full sqlite3 capability surface)."""

from __future__ import annotations

from universal_mind.database_suite import DatabaseSuite, DatabaseSuiteConnector


def test_execute_creates_a_real_table() -> None:
    suite = DatabaseSuite()
    out = suite.execute("CREATE TABLE tools (name TEXT, capability TEXT)")
    assert out["ok"] is True
    tables = suite.tables()
    assert "tools" in tables["tables"]


def test_insert_many_and_query_roundtrip() -> None:
    suite = DatabaseSuite()
    suite.execute("CREATE TABLE runs (capability TEXT, ok INTEGER)")
    out = suite.insert_many("runs", [
        {"capability": "media", "ok": "1"},
        {"capability": "archive", "ok": "1"},
    ])
    assert out["ok"] is True
    assert out["inserted"] == 2
    q = suite.query("SELECT capability, ok FROM runs ORDER BY capability")
    assert q["ok"] is True
    assert q["count"] == 2
    assert q["rows"][0]["capability"] == "archive"


def test_query_with_where_and_aggregate() -> None:
    suite = DatabaseSuite()
    suite.execute("CREATE TABLE metrics (kind TEXT, value REAL)")
    suite.insert_many("metrics", [
        {"kind": "latency", "value": "10"},
        {"kind": "latency", "value": "30"},
        {"kind": "errors", "value": "1"},
    ])
    q = suite.query("SELECT AVG(value) AS avg FROM metrics WHERE kind = 'latency'")
    assert q["ok"] is True
    assert abs(q["rows"][0]["avg"] - 20.0) < 1e-9


def test_data_survives_across_calls_real_persistence() -> None:
    suite = DatabaseSuite()
    suite.execute("CREATE TABLE persistent (k TEXT)")
    suite.insert_many("persistent", [{"k": "v"}])
    # A second query on the SAME suite (same db file) still sees the row.
    q = suite.query("SELECT COUNT(*) AS n FROM persistent")
    assert q["rows"][0]["n"] == 1


def test_bad_sql_fails_clean() -> None:
    suite = DatabaseSuite()
    out = suite.execute("CREATE TABLE bad (")  # syntax error
    assert out["ok"] is False
    q = suite.query("SELECT * FROM nonexistent_table")
    assert q["ok"] is False


def test_query_must_be_select() -> None:
    suite = DatabaseSuite()
    out = suite.query("DROP TABLE something")
    assert out["ok"] is False
    assert "SELECT" in out["error"]


def test_insert_many_mismatched_columns_fails_clean() -> None:
    suite = DatabaseSuite()
    out = suite.insert_many("t", [{"a": 1}, {"b": 2}])
    assert out["ok"] is False
    assert "same columns" in out["error"]


def test_connector_dispatches_operations() -> None:
    conn = DatabaseSuiteConnector()
    created = conn.connect({}, {"operation": "execute", "sql": "CREATE TABLE c (x TEXT)"})
    assert created.ok is True
    inserted = conn.connect({}, {"operation": "insert_many", "table": "c", "rows": [{"x": "1"}]})
    assert inserted.ok is True
    queried = conn.connect({}, {"operation": "query", "sql": "SELECT x FROM c"})
    assert queried.ok is True and queried.output[0]["x"] == "1"


def test_unknown_operation_fails_clean() -> None:
    conn = DatabaseSuiteConnector()
    result = conn.connect({}, {"operation": "drop_database"})
    assert result.ok is False
    assert "unknown operation" in result.error


class TestPersistence:
    def test_persistent_db_survives_a_fresh_suite(self) -> None:
        """persistent=True binds to a FIXED file: a brand-new suite (a new
        session) still sees the data — real survival, not temp-dir death."""
        import os
        from pathlib import Path


        db_dir = Path.home() / ".universal-mind"
        db_file = db_dir / "mind.db"
        marker_table = f"persist_marker_{os.getpid()}"
        a = DatabaseSuite(persistent=True)
        assert Path(a.db_path) == db_file
        assert a.execute(f"CREATE TABLE IF NOT EXISTS {marker_table} (v TEXT)")["ok"]
        assert a.insert_many(marker_table, [{"v": "survives"}])["ok"]
        # A completely fresh suite instance (the next session) sees the marker.
        b = DatabaseSuite(persistent=True)
        q = b.query(f"SELECT COUNT(*) AS n FROM {marker_table}")
        assert q["ok"] is True
        assert q["rows"][0]["n"] >= 1
        # Cleanup the marker so repeated runs stay clean.
        b.execute(f"DROP TABLE {marker_table}")

    def test_connector_persistent_insert_reports_db_path(self) -> None:
        """A persistent insert reports WHERE the data lives (auditable)."""
        import uuid

        conn = DatabaseSuiteConnector(DatabaseSuite(persistent=True))
        table = f"audit_{uuid.uuid4().hex[:8]}"
        out = conn.connect({}, {
            "operation": "insert_many", "table": table,
            "rows": [{"v": "1"}], "persistent": True,
        })
        assert out.ok is True
        assert ".universal-mind" in str(out.output.get("db_path"))
        conn.connect({}, {"operation": "execute", "sql": f"DROP TABLE {table}"})


def test_database_suite_joins_the_synthesis_loop() -> None:
    """The whole SQL program participates in the multi-tool synthesis loop."""
    import universal_mind.real_tool_registry as rtr
    from universal_mind.orchestration import orchestrate
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(name="db", capability="database",
                           connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                           absorbable=True))
    # "database" is an officially registered real capability — no mutation of the
    # shared connector table (the mutate-then-delete pattern caused cross-test
    # contamination that made the desktop app's capability list flake).
    syn = orchestrate(reg, ["database"], connector_factory=rtr.real_connector_factory)
    assert syn.ok is True
    # The default operation is a SELECT; on a fresh db it returns zero rows
    # (a real, honest result — not a failure).
    assert syn.output["synthesized_from"]["database"] == []