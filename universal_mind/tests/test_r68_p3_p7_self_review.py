"""R68 P3-P7 — the self-review answers: day review, since-last-activity,
the honest confession, the last failed run, today's consumption.

The sweep caught «وضعیت کلی من چطور است؟» answering with OLD scheduled
goals, and «چه مدت است روشن نیستم؟» / «چه چیزهایی بلد نیستی؟» /
«آخرین خطای من چه بود؟» / «مصرف امروزم چطور بوده؟» all unrecognized.
Every answer is derived from the real tables/clock — never a cached
string, never a fabricated number.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch as mock_patch

import pytest


@pytest.fixture()
def iso_history():
    """An isolated REAL store with today's rows - the review answers are
    derived from the live tables, so the test feeds the real table and
    asserts the derivation (never a cached string)."""
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.run_history import RunHistory

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r68-review.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent",
                            classmethod(lambda cls: iso)):
        RunHistory().record("گزارش گواه-r68 امروز", ["data"], True,
                           outcome_class="tool")
        RunHistory().record("خطای گواه-r68 امروز", ["chart"], False,
                            outcome_class="heuristic")
        yield iso


class TestTheDayReview:
    def test_it_answers_today_not_the_goal_board(self, iso_history) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("وضعیت کلی من چطور است؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "وضعیت امروز" in rep
        assert "فرمان اجرا کردم" in rep
        assert "زمانبندی" not in rep  # never the old scheduled goals


class TestSinceLastActivity:
    def test_it_answers_from_the_real_gap(self) -> None:

        from universal_mind.persian_router import route_and_run

        p = route_and_run("چه مدت است روشن نیستم؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert any(w in rep for w in ("دقیقه", "ساعت", "ثانیه", "روز", "ثبت نشده"))


class TestTheHonestConfession:
    def test_it_names_the_real_gaps(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چه چیزهایی بلد نیستی؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "مدل زبانی زنده" in rep      # llm knowledge gap, named
        assert "هوای" in rep               # live-data gap, named
        assert "ساختگی" in rep             # the no-fabrication promise


class TestTheLastFailedRun:
    def test_it_names_the_real_last_failure(self, iso_history) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("آخرین خطای من چه بود؟")
        assert p["ok"] is True
        assert "خطای گواه-r68 امروز" in p["agent_report"]
        assert "ناموفق" in p["agent_report"]


class TestTodaysConsumption:
    def test_it_counts_per_route_for_today(self, iso_history) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("مصرف امروزم چطور بوده؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "مصرف امروز" in rep
        assert "ران موفق" in rep
        assert "data" in rep  # the seeded route is named
