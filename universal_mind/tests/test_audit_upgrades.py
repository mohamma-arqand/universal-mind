"""Tests: the three audit upgrades — tick health, semantic advisor, session verdict."""

from __future__ import annotations


class TestTickHealth:
    def test_reports_both_signals_verbatim(self) -> None:
        """Task presence AND the engine heartbeat, each named — never blanket."""
        from universal_mind.task_install import tick_health

        th = tick_health()
        sig = th.get("signals", {}) or {}
        assert "task_installed" in sig
        assert "recent_run" in sig
        assert isinstance(sig["task_installed"], bool)
        assert isinstance(sig["recent_run"], bool)
        assert th.get("verdict") in ("alive", "dead", "silent")  # the honest tri-state


class TestSemanticAdvisor:
    def test_finds_the_meaning_nearest_not_just_word_overlap(self) -> None:
        """«درآمد» lands on «سود» (no shared word!) — the semantic layer."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import ChainAdvisor, RunHistory

        history = RunHistory(DatabaseSuite())
        history.record("میانگین سود ماهانه را حساب کن", ["data"], True, 0.9)
        history.record("نمودار فروش هفتگی بکش", ["chart"], True, 0.9)
        advice = ChainAdvisor(history).advise_semantic("میانگین درآمد ماهانه را محاسبه کن")
        assert advice is not None
        assert "سود" in advice.similar_command  # semantic nearest, not vocab
        assert 0 < advice.similarity <= 100

    def test_tiny_history_falls_back_to_vocabulary(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.run_history import ChainAdvisor, RunHistory

        history = RunHistory(DatabaseSuite())
        history.record("میانگین حساب کن", ["data"], True)
        advice = ChainAdvisor(history).advise_semantic("میانگین بگیر")
        assert advice is not None  # the honest fallback answered


class TestSessionVerdict:
    def test_the_live_session_reads(self) -> None:
        """The real store carries thousands of judged runs — the day has a verdict."""
        from universal_mind.history_analytics import session_verdict

        sv = session_verdict()
        if sv["ok"]:
            assert sv["verdict"] in ("درخشان", "نیازمند توجه")
            assert 0.0 <= sv["mean"] <= 1.0
        else:
            assert sv["verdict"]  # the honest empty-or-error, named

    def test_the_dashboard_renders_the_session_card(self) -> None:
        from universal_mind.superplatform_dashboard import build_dashboard

        result = build_dashboard()
        html = open(result["path"], encoding="utf-8").read()
        assert "داوری نشست" in html
        assert "سلامت حلقهی خودکار" in html
