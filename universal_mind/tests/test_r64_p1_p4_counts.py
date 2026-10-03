"""R64 P1-P4 — real counts, the spoken cancel, negative subtraction, «کمک».

The sweep's live findings (three of them LIES, which are worse than dead
sentences):
- «چند تا یادآور دارم؟» answered «۴۵۴۱۶ اجرا ثبت شده» — a real number
  about the WRONG thing (the count block fell to run_history for every
  subject). Each noun now counts its own table.
- «۵ منهای ۹ را حساب کن» answered «میانگین ۲ عدد برابر ۷» — subtraction
  was missing from the data-suite's scalar table, so the sentence fell
  to a mean. Subtract is real now; the «چند می‌شود؟» question shape
  reaches the engine.
- «اشتباه شد، لغو کن» and «کمک» were dead — the gates took only the
  bare forms.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_counts():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM learned_vocab WHERE word = 'زرشک-r64'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM learned_vocab WHERE word = 'زرشک-r64'")


class TestTheRealCounts:
    def test_a_reminder_count_is_not_a_run_count(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۷ گواه-r64 را بدهکار کن")
        p = route_and_run("چند تا یادآور دارم؟")
        rep = p["agent_report"]
        assert "یادآور داری" in rep
        assert "اجرا ثبت شده" not in rep  # the wrong-thing answer is gone

    def test_a_word_count_answers_from_learned_vocab(self) -> None:
        from universal_mind.learned_vocab import teach
        from universal_mind.persian_router import route_and_run

        teach("زرشک-r64", "داده")
        p = route_and_run("چند تا واژه از من یاد گرفتی؟")
        assert "۱ واژه" in p["agent_report"]
        assert "زرشک-r64" in p["agent_report"]  # the newest is named

    def test_a_file_count_answers_from_the_file_runs(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند تا فایل تا حالا ساختی؟")
        rep = p["agent_report"]
        assert ("بار فایل نوشتهام" in rep) or ("هیچ فایلی نساختهام" in rep)
        assert "اجرا ثبت شده" not in rep


class TestNegativeSubtraction:
    def test_subtraction_is_real_not_a_mean(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۵ منهای ۹ را حساب کن")
        assert p["ok"] is True
        assert "نتیجه -۴" in p["agent_report"] or "نتیجه −۴" in p["agent_report"]

    def test_the_question_shape_reaches_the_engine(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۵ منهای ۹ چند می‌شود؟")
        assert p["ok"] is True
        assert "میانگین" not in p["agent_report"]
        assert "نتیجه -۴" in p["agent_report"] or "نتیجه −۴" in p["agent_report"]

    def test_addition_question_still_works(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("جمع ۲ و ۳ چند می‌شود؟")
        assert p["ok"] is True
        assert "نتیجه ۵" in p["agent_report"]


class TestTheSpokenGates:
    def test_the_prefix_cancel_answers(self) -> None:
        from universal_mind.persian_router import route_and_run

        # a real run first, so the cancel has something to name
        route_and_run("جمع ۲ و ۳ را حساب کن")
        p = route_and_run("اشتباه شد، لغو کن")
        assert p is not None
        rep = p["agent_report"]
        # honest either way: the refusal naming the last run, or the
        # empty-store refusal — never «نشناختم».
        assert ("لغوِ خودکار نمی‌کنم" in rep) or ("پیدا نکردم" in rep)
        assert "نشناختم" not in rep

    def test_help_is_the_capability_list(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کمک")
        assert p["ok"] is True
        assert "قابلیت" in p["agent_report"]
        assert "نشناختم" not in p["agent_report"]
