"""Tests: the synthesis-completion hint — grounded in real history."""

from __future__ import annotations

from universal_mind.run_history import ChainAdvisor, RunHistory


class TestCompletionHint:
    @staticmethod
    def _history() -> "RunHistory":
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import RunHistory

        return RunHistory(DatabaseSuite())

    def test_half_chain_gets_the_completed_hint(self) -> None:
        """'نمودار' alone advises chart; the FULL chart→pdf exists in history
        with a real win → the completion hint fires."""
        history = self._history()
        history.record("نمودار خطی بساز", ["chart"], True, excellence=0.9)
        history.record("نمودار بساز و گزارشش کن", ["chart", "pdf"], True, excellence=1.0)
        hint = ChainAdvisor(history).completion_hint("نمودار خطی بساز")
        assert hint is not None
        assert "کاملش کنی" in hint
        assert "chart → pdf" in hint or "نمودار" in hint

    def test_no_completed_history_no_hint(self) -> None:
        """The full chain has NEVER succeeded → no hint (never a guess)."""
        history = self._history()
        history.record("نمودار خطی بساز", ["chart"], True, excellence=0.9)
        assert ChainAdvisor(history).completion_hint("نمودار خطی بساز") is None

    def test_already_complete_chain_no_hint(self) -> None:
        """A chain that already ships (chart→pdf) needs no completion."""
        history = self._history()
        history.record("نمودار بساز و گزارشش کن", ["chart", "pdf"], True, excellence=1.0)
        assert ChainAdvisor(history).completion_hint("نمودار بساز و گزارشش کن") is None

    def test_unknown_command_no_hint(self) -> None:
        assert ChainAdvisor(self._history()).completion_hint("سلام") is None
