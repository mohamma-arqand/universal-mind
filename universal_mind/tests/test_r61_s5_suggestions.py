"""R61-S5 — intent-aware suggestions and the colloquial sentence shapes.

The review measured «یادم باشی…» suggesting «سایت/لبه/برش» (edit-distance
soup) and a whole band of real speech («صبح بخیر», «ممنون که کمک کردی»,
«یادم بشه…») falling dead to «نشناختم». Three laws now hold:

1. DOMAIN LENS FIRST: a sentence naming a domain gets that domain's starter
   command as the top suggestion - a suggestion that teaches the shape.
2. COLLOQUIAL REMINDER FORMS: باشی/بشه/بشی/بادی/باش/یادت نره all register.
3. SENTENCE-SHAPED SOCIAL: the keyword inside a longer sentence is still the
   same intent (thanks wrapped in a sentence, صبح/شب بخیر, «تو خسته نیستی؟»).
"""

from __future__ import annotations

from typing import Iterator

import pytest

from universal_mind.persian_router import route_and_run
from universal_mind.spelling_recovery import suggest_for


@pytest.fixture()
def probe_reminder() -> Iterator[None]:
    route_and_run("یادم باشه پس‌فردا ساعت ۶ گواه-آزمون-s5")
    yield
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-آزمون-s5%'")


class TestIntentAwareSuggestions:
    def test_a_reminder_sentence_suggests_the_reminder_recipe(self) -> None:
        s = suggest_for("یادم باشی فردا زنگ بزنم")
        assert s and "یادم بنداز" in s[0]

    def test_an_email_sentence_suggests_the_email_recipe(self) -> None:
        s = suggest_for("ایمیل بزن به رئیس")
        assert s and "ایمیل" in s[0]

    def test_a_typo_chart_still_recovers_by_distance(self) -> None:
        s = suggest_for("نماودار از ۳")
        assert s and "نمودار" in s[0]

    def test_no_domain_falls_back_to_the_old_behaviour(self) -> None:
        s = suggest_for("بلابلا نیمیدونم")
        assert isinstance(s, list) and len(s) <= 3


class TestColloquialReminders:
    def test_bashi_registers(self, probe_reminder) -> None:
        p = route_and_run("یادم باشی فردا ساعت ۹ تماس")
        assert p.get("ok") is True and "ثبت شد" in p["agent_report"]

    def test_beshe_registers(self, probe_reminder) -> None:
        p = route_and_run("یادم بشه فردا ساعت ۹ گواه-آزمون-s5")
        assert p.get("ok") is True and "ثبت شد" in p["agent_report"]

    def test_a_defaulted_hour_confesses_it_is_a_default(self) -> None:
        p = route_and_run("یادم باشه پس‌فردا زنگ بزنم")
        assert p.get("ok") is True
        assert "پیش‌فرض" in p["agent_report"]

    def test_a_named_hour_does_not_carry_the_default_note(self) -> None:
        p = route_and_run("یادم باشه پس‌فردا ساعت ۷ زنگ بزنم")
        assert p.get("ok") is True
        assert "پیش‌فرض" not in p["agent_report"]


class TestSentenceShapedSocial:
    def test_thanks_wrapped_in_a_sentence_answers(self) -> None:
        p = route_and_run("ممنون که کمک کردی")
        assert p.get("ok") is True and "خواهش" in p["agent_report"]

    def test_morning_greeting_answers(self) -> None:
        p = route_and_run("صبح بخیر")
        assert p.get("ok") is True and "صبح بخیر" in p["agent_report"]

    def test_evening_greeting_answers(self) -> None:
        p = route_and_run("شب بخیر")
        assert p.get("ok") is True and "شب بخیر" in p["agent_report"]

    def test_the_are_you_tired_question_answers_honestly(self) -> None:
        p = route_and_run("تو خسته نیستی؟")
        assert p.get("ok") is True and "خسته نمیشوم" in p["agent_report"]
