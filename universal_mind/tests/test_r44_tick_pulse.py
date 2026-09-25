"""Tests: R44 item 13 — the heartbeat HISTORY, not just "now".

Live laws:
1. The window is exactly N local days, oldest first, and a silent day is a
   ZERO row — never a missing one (silence is the signal).
2. An empty today does not break a real streak (the platform is not dead at
   09:00 because nothing happened since midnight).
3. The answer NAMES the silent days instead of hiding them.
"""

from __future__ import annotations

import datetime as _dt
import tempfile
from pathlib import Path
from typing import Any


def _db_with_days(backs: tuple[int, ...]) -> Any:
    """An isolated store with one run `back` days ago for each entry."""
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "pulse.db"))
    RunHistory(db)
    now = _dt.datetime.now()
    for back in backs:
        ts = (now - _dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, created_at) "
            f"VALUES ('x', 'data', 1, 1.0, '{ts}')"
        )
    return db


class TestTheWindow:
    def test_the_window_is_n_days_oldest_first(self) -> None:
        from universal_mind.tick_pulse import pulse_window

        db = _db_with_days((0, 2))
        window = pulse_window(days=7, db=db)
        assert len(window) == 7
        assert window[-1].day == _dt.date.today().isoformat(), "newest day is today"
        days = [d.day for d in window]
        assert days == sorted(days), "oldest first"
        assert window[-1].runs == 1

    def test_a_silent_day_is_a_zero_row_not_a_gap(self) -> None:
        from universal_mind.tick_pulse import pulse_window

        db = _db_with_days((0,))
        window = pulse_window(days=5, db=db)
        assert len(window) == 5
        assert sum(1 for d in window if not d.awake) == 4, [d.day for d in window]


class TestTheStreak:
    def test_an_empty_today_does_not_break_the_streak(self) -> None:
        from universal_mind.tick_pulse import alive_streak, pulse_window

        db = _db_with_days((1, 2, 3))  # nothing today, three full days before
        assert alive_streak(pulse_window(days=7, db=db)) == 3

    def test_a_silent_yesterday_breaks_it(self) -> None:
        from universal_mind.tick_pulse import alive_streak, pulse_window

        db = _db_with_days((0, 2))  # today and 2 days ago, yesterday empty
        assert alive_streak(pulse_window(days=7, db=db)) == 1

    def test_an_empty_store_has_no_streak(self) -> None:
        from universal_mind.tick_pulse import alive_streak, pulse_window

        db = _db_with_days(())
        assert alive_streak(pulse_window(days=7, db=db)) == 0


class TestTheAnswer:
    def test_silence_is_named_not_hidden(self) -> None:
        from universal_mind.tick_pulse import pulse_report, pulse_sentence

        db = _db_with_days((0, 3))
        sentence = pulse_sentence(pulse_report(db=db))
        assert "زنده" in sentence
        assert "سکوت" in sentence, sentence  # the gap is announced
        silent = pulse_report(db=db)["silent"]
        assert silent and all(day in sentence for day in silent), sentence

    def test_a_dead_heartbeat_says_so(self) -> None:
        from universal_mind.tick_pulse import pulse_report, pulse_sentence

        db = _db_with_days(())
        sentence = pulse_sentence(pulse_report(db=db))
        assert "قطع" in sentence, sentence

    def test_persian_digits_are_used(self) -> None:
        from universal_mind.tick_pulse import pulse_report, pulse_sentence

        db = _db_with_days((0, 1, 2))
        sentence = pulse_sentence(pulse_report(db=db))
        assert "۳" in sentence and "3" not in sentence.split("(")[0], sentence


class TestTheQuestion:
    """The operator's real question, through the real router."""

    def test_the_router_answers_the_heartbeat_question(self) -> None:
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        db = _db_with_days((0, 1, 2))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: db)):
            from universal_mind.persian_router import route_and_run

            for phrase in ("چند روز است زنده؟", "تپش چطور است؟", "چند روزه زندهای؟"):
                p: Any = route_and_run(phrase)
                assert p["route"] == ["reflexive"], phrase
                assert "زنده" in p["agent_report"], (phrase, p["agent_report"])
                assert "نشناختم" not in p["agent_report"], phrase

