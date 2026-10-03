"""R66 P6 — «تنظیمات نمودار را تغییر بده به خطی»: a SETTINGS-CHANGE is a
preference, not a draw.

The sweep caught the sentence routed to chart where it honestly (but
wrongly) refused: the operator was naming what FUTURE charts should
look like, not asking to draw one now. The preference parser now takes
the settings-change shape (تنظیمات/پیش‌فرض + تغییر/عوض + the kind).
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def restore_chart_kind():
    from universal_mind import operator_preferences as prefs

    before = prefs.get("chart_kind")
    yield
    if before is None:
        from universal_mind.database_suite import DatabaseSuite

        DatabaseSuite(persistent=True).execute(
            "DELETE FROM operator_preferences WHERE key = 'chart_kind'")
    else:
        prefs.set("chart_kind", before)


class TestSettingsChangeIsAPreference:
    def test_it_stores_not_draws(self, restore_chart_kind) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("تنظیمات نمودار را تغییر بده به خطی")
        assert p["ok"] is True
        assert p["route"] == ["preference"]  # NOT chart
        assert "یاد گرفتم" in p["agent_report"]

    def test_the_kind_is_really_stored(self, restore_chart_kind) -> None:
        from universal_mind import operator_preferences as prefs
        from universal_mind.persian_router import route_and_run

        route_and_run("تنظیمات نمودار را تغییر بده به میله‌ای")
        assert prefs.get("chart_kind") == "bar"

    def test_a_plain_chart_ask_is_still_a_draw(self) -> None:
        from universal_mind.persian_router import route

        caps = route("نمودار خطی از ۳ و ۷ بکش").capabilities
        assert "chart" in caps and "preference" not in caps
