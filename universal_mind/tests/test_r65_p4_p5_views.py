"""R65 P4+P5 — the contact book view; the weekday from the real clock.

Both were measured dead sentences. The contact book lists the names
the operator TAUGHT (never fabricated); the weekday answer derives
from datetime.now() with the Persian week starting شنبه (Saturday).
"""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM contacts WHERE name LIKE '%گواه-r65%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM contacts WHERE name LIKE '%گواه-r65%'")


class TestTheContactBookView:
    def test_lists_the_real_book(self) -> None:
        from universal_mind.contacts import save
        from universal_mind.persian_router import route_and_run

        save("گواه-r65", "w65@example.com")
        p = route_and_run("مخاطبهام را نشان بده")
        rep = p["agent_report"]
        assert p["route"] == ["reflexive"]
        assert "مخاطب دارم" in rep
        assert "گواه-r65" in rep and "w65@example.com" in rep

    def test_empty_book_teaches_the_recipe(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        DatabaseSuite.shared_persistent().execute(
            "DELETE FROM contacts WHERE name LIKE '%گواه-r65%'")
        p = route_and_run("لیست مخاطبینم چیست؟")
        assert "خالی است" in p["agent_report"]
        assert "یادت باشد" in p["agent_report"]  # the enabling sentence


class TestTheWeekdayAnswer:
    def test_today_matches_the_independent_computation(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("امروز چندشنبه است؟")
        rep = p["agent_report"]
        # the INDEPENDENT computation (never today's literal answer):
        _DAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
        expected_today = _DAYS[(datetime.now().weekday() + 2) % 7]
        expected_tomorrow = _DAYS[(datetime.now().weekday() + 3) % 7]
        assert f"امروز {expected_today} است" in rep
        assert f"فردا {expected_tomorrow}" in rep
