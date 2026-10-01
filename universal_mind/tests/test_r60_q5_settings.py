"""R60 Q5 — «تنظیماتت را نشان بده»: the operator's own settings, read-only.

The store is REAL (operator_preferences in mind.db); secret-looking keys are
masked, the count is honest, and the empty store says so.
"""

from __future__ import annotations

from universal_mind import operator_preferences as op
from universal_mind.reflexive import answer_reflexive


class TestAllPrefs:
    def test_a_secret_looking_key_is_masked(self) -> None:
        # read-only view via the module — set/cleanup with named keys
        op.set("probe_secret_token", "abc123")
        try:
            prefs = op.all_prefs()
            assert prefs.get("probe_secret_token") == "(مخفی — به نظر راز می‌رسد)"
        finally:
            from universal_mind.database_suite import DatabaseSuite

            db = DatabaseSuite(persistent=True)
            db.execute(
                "DELETE FROM operator_preferences WHERE key = 'probe_secret_token'")
        assert "probe_secret_token" not in op.all_prefs()  # cleaned, pinned

    def test_a_normal_pref_shows_its_value(self) -> None:
        op.set("probe_kind", "line")
        try:
            assert op.all_prefs().get("probe_kind") == "line"
        finally:
            from universal_mind.database_suite import DatabaseSuite

            db = DatabaseSuite(persistent=True)
            db.execute("DELETE FROM operator_preferences WHERE key = 'probe_kind'")

    def test_an_oversized_value_is_masked_too(self) -> None:
        op.set("probe_big", "x" * 200)
        try:
            assert "مخفی" in op.all_prefs().get("probe_big", "")
        finally:
            from universal_mind.database_suite import DatabaseSuite

            db = DatabaseSuite(persistent=True)
            db.execute("DELETE FROM operator_preferences WHERE key = 'probe_big'")


class TestReflexiveAnswer:
    def test_the_settings_question_lists_the_real_store(self) -> None:
        op.set("probe_visible", "on")
        try:
            ans = answer_reflexive("تنظیماتت را نشان بده")
            assert ans is not None
            rep = ans["agent_report"]
            assert "تنظیم" in rep and "probe_visible = on" in rep
        finally:
            from universal_mind.database_suite import DatabaseSuite

            db = DatabaseSuite(persistent=True)
            db.execute("DELETE FROM operator_preferences WHERE key = 'probe_visible'")

    def test_the_word_settings_alone_is_not_a_listing(self) -> None:
        # «تنظیمات» without a show-verb must not trigger (narrow gate)
        assert answer_reflexive("تنظیمات") is None
