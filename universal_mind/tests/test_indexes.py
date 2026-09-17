"""Tests: query-acceleration indexes on the persistent store."""

from __future__ import annotations


class TestIndexes:
    def test_the_indexes_exist_on_the_live_store(self) -> None:
        from universal_mind.run_history import RunHistory

        RunHistory()  # the constructor creates them idempotently
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite(persistent=True)
        q = db.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        names = {r["name"] for r in q["rows"]}
        assert "idx_history_succeeded" in names
        assert "idx_history_route" in names
        assert "idx_lessons_capability" in names

    def test_indexed_queries_still_answer_correctly(self) -> None:
        """Speed must never change semantics — the advisor answers as before."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import ChainAdvisor, RunHistory

        history = RunHistory(DatabaseSuite())  # temp store (indexes apply too)
        history.record("میانگین و نمودار", ["data", "chart"], True, excellence=0.9)
        advice = ChainAdvisor(history).advise("میانگین و نمودار بساز")
        assert advice is not None
        assert advice.route == ("data", "chart")
