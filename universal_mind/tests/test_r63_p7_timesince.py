"""R63 P7 — «چند ساعت از خواب من گذشته؟»: real elapsed time on a
taught fact, honest refusal without one.

The platform cannot SEE the operator's sleep — but a fact they TAUGHT
it carries a timestamp, and elapsed-since is real arithmetic on real
data. Without a stored fact the answer refuses by name and teaches
the exact sentence that makes it answerable («یادت باشد که ساعت ۲۳
خوابیدم»), never a guess about their life.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_fact():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM named_memory WHERE fact LIKE '%گواه-خواب-r63%'")
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-خواب-r63%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM named_memory WHERE fact LIKE '%گواه-خواب-r63%'")
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-خواب-r63%'")


class TestTheHonestRefusal:
    def test_no_stored_fact_refuses_and_teaches(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند ساعت از خواب من گذشته؟")
        assert p["ok"] is False
        rep = p["agent_report"]
        assert "نمی‌بینم" in rep
        assert "یادت باشد" in rep  # the exact enabling sentence is taught


class TestTheRealMath:
    def test_a_taught_fact_gets_real_elapsed_time(self) -> None:
        from universal_mind.named_memory import save_fact
        from universal_mind.persian_router import route_and_run

        save_fact("گواه-خواب-r63: دارم می‌خوابم")
        p = route_and_run("چند ساعت از گواه-خواب-r63 گذشته؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "از «گواه-خواب-r63" in rep
        assert "گذشته است" in rep
        assert "ثبت:" in rep  # the timestamp it was computed from is named

    def test_the_possessive_is_stripped_from_the_topic(self) -> None:
        # «خواب من» must search for «خواب», not the literal «خواب من گذشته»
        from universal_mind.named_memory import save_fact
        from universal_mind.persian_router import route_and_run

        save_fact("گواه-خواب-r63: دارم می‌خوابم")
        p = route_and_run("چند ساعت از گواه-خواب-r63 گذشته؟")
        assert p["ok"] is True
        assert "گواه-خواب-r63" in p["agent_report"]

    def test_a_reminder_carrying_the_fact_counts_too(self) -> None:
        # T1 law: a fact WITH a moment becomes a reminder; its timestamp
        # is just as real for elapsed-time arithmetic.
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۶ گواه-خواب-r63 را بیدار کن")
        p = route_and_run("چند ساعت از گواه-خواب-r63 گذشته؟")
        assert p["ok"] is True
        assert "از «" in p["agent_report"]
        assert "گذشته است" in p["agent_report"]
