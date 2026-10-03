"""R69 P1-P6 — compound times, the reminder ownership, battery vitals,
sort/extremes, and Persian word-numbers.

Two LIVE wrong answers from the sweep:
- «یک ساعت دیگر یادم بیار گزارش بده» built a 34KB PDF (the «گزارش بده»
  half stole the sentence) while the reminder never registered.
- «چند درصد باتری مانده؟» averaged the extracted_data table's
  EXPERIMENTAL rows as a battery answer.

Plus: compound one-shot times (نیم ساعت، بیست و پنج دقیقه، ۸:۳۰، فردا
صبح), the sort and the extremes as real data operations, and Persian
word-numbers («بیست و پنج بعلاوه هفت» = 32) with the word-boundary law
(«چنده» must never yield a phantom «ده»=10).
"""

from __future__ import annotations

from datetime import datetime



def _cleanup(rows_like: str) -> None:
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite(persistent=True).execute(
        f"DELETE FROM schedules WHERE command LIKE '%{rows_like}%'")


class TestTheRelativeDelta:
    def test_one_hour_other_registers_now_plus_60(self) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.scheduler import list_schedules

        try:
            p = route_and_run("یک ساعت دیگر یادم بیار گزارش بده-r69")
            assert p["ok"] is True
            assert p["route"] == ["scheduler"]  # NOT pdf
            row = next(s for s in list_schedules()
                       if "گزارش بده-r69" in s.command)
            fire = datetime.fromisoformat(row.run_at)
            delta_min = (fire - datetime.now()).total_seconds() / 60
            assert 55 <= delta_min <= 65      # ~one hour from NOW
            assert "PDF" not in p["agent_report"]
        finally:
            _cleanup("گزارش بده-r69")

    def test_half_hour_is_30_minutes(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        shot = parse_one_shot("نیم ساعت دیگر یادم بیار زنگ بزن")
        assert shot is not None and shot["relative_minutes"] == 30

    def test_twenty_five_minutes_word_number(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        shot = parse_one_shot("بیست و پنج دقیقه دیگر زنگ بزن")
        assert shot is not None and shot["relative_minutes"] == 25

    def test_compound_clock_eight_thirty(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        shot = parse_one_shot("ساعت ۸:۳۰ فردا یادم بیار جلسه-r69")
        assert shot is not None
        fire = datetime.fromisoformat(shot["run_at"])
        assert fire.hour == 8 and fire.minute == 30


class TestTheReminderOwnership:
    def test_a_reminder_verb_never_builds_a_document(self) -> None:
        from universal_mind.persian_router import route

        caps = route("یک ساعت دیگر یادم بیار گزارش بده").capabilities
        assert "pdf" not in caps


class TestTheBatteryVital:
    def test_battery_question_is_sysstatus_alone(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند درصد باتری مانده؟")
        assert p["ok"] is True
        assert p["route"] == ["sysstatus"]
        assert "میانگین" not in p["agent_report"]  # never the data mean
        assert "روشن است" in p["agent_report"]     # the real vitals


class TestSortAndExtremes:
    def test_sort_ascending(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("مرتب کن: ۵ و ۲ و ۹")
        assert p["ok"] is True
        assert "مرتب شد (صعودی)" in p["agent_report"]
        assert "۲، ۵، ۹" in p["agent_report"]

    def test_sort_descending(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("ترتیب نزولی ۵ و ۲ و ۹ را نشان بده")
        assert p["ok"] is True
        assert "نزولی" in p["agent_report"]
        assert "۹، ۵، ۲" in p["agent_report"]

    def test_largest_is_a_data_question_not_llm(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("بزرگترین از ۵ و ۹ و ۲ چیست؟")
        assert p["ok"] is True
        assert p["route"] == ["data"]  # NOT llm
        assert "بزرگترین از ۳ عدد: ۹" in p["agent_report"]

    def test_smallest(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کوچکترین از ۵ و ۹ و ۲ چیست؟")
        assert p["ok"] is True
        assert "کوچکترین از ۳ عدد: ۲" in p["agent_report"]


class TestSpokenNumbers:
    def test_twenty_five_plus_seven(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("بیست و پنج بعلاوه هفت چنده؟")
        assert p["ok"] is True
        assert "نتیجه ۳۲" in p["agent_report"]

    def test_the_word_boundary_law_no_phantom_ten(self) -> None:
        from universal_mind.persian_params import extract_numbers

        assert extract_numbers("بیست و پنج بعلاوه هفت چنده؟") == [25.0, 7.0]
        assert extract_numbers("جمع ۲ و ۵ چنده؟") == [2.0, 5.0]

    def test_thousand_scales(self) -> None:
        from universal_mind.persian_params import extract_numbers

        assert extract_numbers("دو هزار") == [2000.0]
