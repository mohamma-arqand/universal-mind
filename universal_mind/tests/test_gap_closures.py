"""Tests: the three gap-closures — honest outcome classes, poison detection, everyday words."""

from __future__ import annotations

from contextlib import AbstractContextManager


class TestOutcomeClass:
    def test_environment_refusal_is_not_a_failure(self) -> None:
        """A no-Persian-voice speech is 'blocked_env' — the predictor's
        history must never learn pessimism from the environment."""
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        # simplest honest route: record directly through RunHistory and read back
        from universal_mind.run_history import RunHistory

        history = RunHistory(suite)
        history.record("بلند بخوان", ["speech"], False, outcome_class="blocked_env")
        q = suite.query("SELECT outcome_class, succeeded FROM run_history ORDER BY id DESC LIMIT 1")
        row = q["rows"][0]
        assert row["outcome_class"] == "blocked_env"
        assert int(row["succeeded"]) == 0

    def test_the_predictor_ignores_blocked_env_rows(self) -> None:
        """A chain whose only 'failures' were blocked_env reads as strong."""
        from unittest.mock import patch as mock_patch

        import universal_mind.success_predictor as sp_mod
        from universal_mind.success_predictor import predict_success

        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        # the predictor holds its OWN import-time DatabaseSuite name — patch
        # THAT, not database_suite's (a from-import binds early).
        with mock_patch.object(sp_mod, "DatabaseSuite", lambda persistent=True: suite):
            from universal_mind.run_history import RunHistory

            RunHistory(suite).record("بلند بخوان", ["speech", "data"], False, outcome_class="blocked_env")
            RunHistory(suite).record("بلند بخوان", ["speech", "data"], True, excellence=1.0)
            RunHistory(suite).record("بلند بخوان", ["speech", "data"], True, excellence=1.0)
            p = predict_success(("speech", "data"))
        # two real wins, zero real failures → Laplace (2+1)/(2+2) = 0.75, tier medium+
        assert p.success_probability >= 0.75
        assert p.tier in ("strong", "medium")


class TestPoisonDetection:
    def _isolated(self) -> "AbstractContextManager[object]":
        from unittest.mock import patch as mock_patch

        import universal_mind.agent_loop as agent_mod
        from universal_mind.database_suite import DatabaseSuite

        suite = DatabaseSuite()
        return mock_patch.object(agent_mod, "_store", lambda: suite)

    def test_three_same_step_stops_poison_the_goal(self) -> None:
        from universal_mind.agent_loop import POISON_THRESHOLD, _poisoned_goals, run_goal, start_goal

        with self._isolated():
            started = start_goal(
                "هدف: زهرآلود", ("این فرمان هیچ قابلیتی ندارد XYZQ",)
            )
            for _ in range(POISON_THRESHOLD):
                run_goal(started["goal_id"])
            # outcomes recorded 3 fails at index 0 → poisoned
            assert started["goal_id"] in _poisoned_goals()

    def test_below_threshold_is_not_poisoned(self) -> None:
        from universal_mind.agent_loop import POISON_THRESHOLD, _poisoned_goals, run_goal, start_goal

        with self._isolated():
            started = start_goal("هدف: سالم", ("این فرمان هیچ قابلیتی ندارد XYZQ",))
            for _ in range(POISON_THRESHOLD - 1):
                run_goal(started["goal_id"])
            assert started["goal_id"] not in _poisoned_goals()

    def test_continue_bde_refuses_poison_with_warning(self) -> None:
        """«ادامه بده» on a poisoned goal warns instead of blind re-running."""
        import universal_mind.agent_loop as agent_mod
        from universal_mind.persian_router import route_and_run
        from universal_mind.database_suite import DatabaseSuite

        from unittest.mock import patch as mock_patch

        import universal_mind.database_suite as ds_mod

        suite = DatabaseSuite()
        # BOTH lenses must see the SAME suite: the router opens the store
        # through database_suite AND the goal loop through agent._store.
        with mock_patch.object(agent_mod, "_store", lambda: suite), \
             mock_patch.object(ds_mod, "DatabaseSuite", lambda persistent=False: suite):
            started = agent_mod.start_goal("هدف: زهرآلود تست", ("این فرمان هیچ قابلیتی ندارد XYZQ",))
            from universal_mind.agent_loop import POISON_THRESHOLD

            for _ in range(POISON_THRESHOLD):
                agent_mod.run_goal(started["goal_id"])
            payload = route_and_run("ادامه بده")
        assert "زهرآلود" in payload["agent_report"]
        assert "اصلاح" in payload["agent_report"]  # the remedy, stated


class TestEverydayVocabulary:
    def test_the_everyday_words_route(self) -> None:
        from universal_mind.persian_router import route_and_run

        cases = [
            ("یادداشت کن که کار تمام شد", "clipboard"),
            ("هشدار بده که حاضر است", "notify"),
            ("چاپ کن", "pdf"),
            ("جستجو کن", "webfetch"),
        ]
        for command, expected in cases:
            payload = route_and_run(command)
            assert expected in payload["route"], f"{command!r} → {payload['route']}"

    def test_vocab_grew_past_the_old_baseline(self) -> None:
        from universal_mind.persian_router import _VOCAB

        for word in ("چاپ کن", "ترجمه", "جستجو", "تقویم", "یادداشت", "هشدار"):
            assert any(word == v or word in v for v, _ in _VOCAB), word
