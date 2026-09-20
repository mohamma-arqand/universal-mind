"""Tests: R37-L4 — operator preferences: stored, applied, never overriding."""

from __future__ import annotations

from unittest.mock import patch as mock_patch

import tempfile
from pathlib import Path

from universal_mind.database_suite import DatabaseSuite
from universal_mind import operator_preferences as prefs


def _isolated_db() -> DatabaseSuite:
    """ONE stable file for the whole test — DatabaseSuite() bare would build
    a NEW temp db per call, making set invisible to get. The preferences
    table is created HERE because patching _db skips the module's own
    CREATE (that lives inside the un-patched _db)."""
    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "prefs.db"))
    db.execute(
        "CREATE TABLE IF NOT EXISTS operator_preferences ("
        "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return db


class TestOperatorPreferences:
    def test_preference_lifecycle_real_db(self) -> None:
        """set → get on a REAL isolated db — the memory persists."""
        db = _isolated_db()
        with mock_patch.object(prefs, "_db", lambda: db):
            assert prefs.get("chart_kind") is None  # absence is honest
            prefs.set("chart_kind", "bar")
            assert prefs.get("chart_kind") == "bar"
            prefs.set("chart_kind", "pie")  # upsert
            assert prefs.get("chart_kind") == "pie"

    def test_parse_preference_shapes(self) -> None:
        assert prefs.parse_preference("همیشه نمودار میله‌ای دوست دارم") == ("chart_kind", "bar")
        assert prefs.parse_preference("همیشه نمودار دایرهای بهتره") == ("chart_kind", "pie")
        assert prefs.parse_preference("نمودار میله‌ای بساز") is None  # no «همیشه»
        assert prefs.parse_preference("همیشه صبح چای میخورم") is None  # nothing we shape

    def test_apply_fills_only_implicit(self) -> None:
        """A stored preference fills a default; an explicit kind wins."""
        db = _isolated_db()
        with mock_patch.object(prefs, "_db", lambda: db):
            prefs.set("chart_kind", "bar")
            filled = prefs.apply_to({"chart": {"operation": "line"}})
            assert filled["chart"]["operation"] == "bar"
            # the operator SAID خطی — the word wins over the memory
            explicit = prefs.apply_to({"chart": {"operation": "line", "kind_explicit": True}})
            assert explicit["chart"]["operation"] == "line"

    def test_apply_never_mutates_input(self) -> None:
        db = _isolated_db()
        with mock_patch.object(prefs, "_db", lambda: db):
            prefs.set("chart_kind", "bar")
            src = {"chart": {"operation": "line"}}
            prefs.apply_to(src)
            assert src["chart"]["operation"] == "line"  # untouched

    def test_router_stores_and_applies_end_to_end(self) -> None:
        """«همیشه نمودار میله‌ای دوست دارم» → the NEXT plain chart is a bar."""
        from universal_mind.persian_router import route_and_run

        ack = route_and_run("همیشه نمودار میله‌ای دوست دارم")
        assert ack["route"] == ["preference"]
        assert "یاد گرفتم" in ack["agent_report"]
        # restore the line default so other tests stay deterministic
        route_and_run("همیشه نمودار خطی دوست دارم")