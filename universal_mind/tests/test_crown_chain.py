"""Tests: the crowning bridge — the platform's best chain, elected as a standard."""

from __future__ import annotations

import pytest


class TestCrownStandingChain:
    @pytest.mark.live_store  # type: ignore[untyped-decorator]
    def test_the_live_best_chain_is_crowned_through_the_real_election(self) -> None:
        """chart → pdf (1300+ wins, excellence 1.0) passes the StandardKeeper
        election — the justice hard-gate included — and is crowned honestly."""
        from universal_mind.history_analytics import crown_standing_chain

        result = crown_standing_chain()
        assert result["ok"] is True
        # the live history crowns the real dominant chain
        assert result["crowned"] is True
        assert result["chain"] == "chart → pdf"
        assert result["wins"] >= 3
        assert result["decision"]  # the election's own reasoning, verbatim

    def test_no_qualifier_crowns_nothing(self) -> None:
        """A fresh history with no repeated winner crowns NOTHING — the
        election is never a rubber stamp."""
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        import universal_mind.history_analytics as ha

        suite = DatabaseSuite()
        ctx: AbstractContextManager[object] = mock_patch.object(
            RunHistory, "__init__", lambda self, db=None: object.__setattr__(self, "_db", suite)
        )
        with ctx:
            RunHistory().record("تنها یک بار", ["data"], True, excellence=1.0)
            result = ha.crown_standing_chain()
        assert result["ok"] is False
        assert "سزاوار" in result["error"]
