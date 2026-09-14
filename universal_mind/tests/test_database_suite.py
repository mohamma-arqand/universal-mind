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
    rtr._REAL_CONNECTORS["database"] = DatabaseSuiteConnector  # one-line registration
    try:
        # The default operation is a SELECT; on a fresh db it returns zero rows
        # (a real, honest result — not a failure).
        syn = orchestrate(reg, ["database"], connector_factory=rtr.real_connector_factory)
        assert syn.ok is True
        assert syn.output["synthesized_from"]["database"] == []
    finally:
        del rtr._REAL_CONNECTORS["database"]