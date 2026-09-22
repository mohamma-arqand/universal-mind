"""Tests: the standing-chain bridge — repeated winners deserve standards."""

from __future__ import annotations

import pytest


class TestStandingChain:
    @pytest.mark.live_store  # type: ignore[untyped-decorator]
    def test_a_repeated_winner_is_crowned_from_real_history(self) -> None:
        """The LIVE store's dominant chain qualifies (chart→pdf, hundreds of
        wins at 1.0 — verified against the real operator history)."""
        from universal_mind.history_analytics import standing_chain

        result = standing_chain()
        # the live history genuinely contains a 3+ win / >=0.90 chain
        assert result["ok"] is True
        assert result["wins"] >= 3
        assert result["mean_excellence"] >= 0.90
        assert result["route"]  # a real route, named

    def test_no_qualifier_is_honest_none(self) -> None:
        """A fresh history with no repeated winners crowns NOTHING."""
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.history_analytics import standing_chain
        from universal_mind.run_history import RunHistory

        suite = DatabaseSuite()
        ctx: AbstractContextManager[object] = mock_patch.object(
            RunHistory, "__init__", lambda self, db=None: object.__setattr__(self, "_db", suite)
        )
        with ctx:
            history = RunHistory()
            history.record("تنها یک بار", ["data"], True, excellence=1.0)
            result = standing_chain()
        assert result["ok"] is False
        assert "سزاوار" in result["error"]  # the honest refusal
