"""R62 T2 — knowledge questions without data: named refusal, real roads.

«هوا تهران چطوره؟» fell to «نشناختم» (no vocabulary word) — but the
sentence IS understood: it asks the WORLD, and the world is not wired.
The honest answer names the missing DATA, never guesses a number, gives
both real roads (live model / fetch-a-page), and harvests the question.
"""

from __future__ import annotations

import pytest

from universal_mind.reflexive import answer_reflexive


def _refusal_of(cmd: str) -> str:
    ans = answer_reflexive(cmd)
    assert ans is not None, cmd
    return ans["agent_report"]


@pytest.fixture(autouse=True)
def _clean_harvest():
    # R42 law: inside a test, shared_persistent() is the ISOLATED temp
    # store (conftest re-points it) — the harvest writes THERE, so the
    # checks and the cleanup must read/write the same suite.
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite.shared_persistent()
    db.execute("DELETE FROM unknown_terms WHERE term LIKE '%هوا%'")  # clean start
    yield
    db.execute("DELETE FROM unknown_terms WHERE term LIKE '%هوا%'")  # named cleanup


class TestNamedRefusal:
    def test_weather_is_refused_with_the_topic_named(self) -> None:
        rep = _refusal_of("هوا تهران چطوره؟")
        assert "«هوا»" in rep and "دادهٔ بیرونی" in rep

    def test_gold_price_is_refused_not_computed(self) -> None:
        rep = _refusal_of("قیمت طلا چنده؟")
        assert "حدسی نمی‌سازم" in rep
        assert "نتیجه" not in rep  # never a fabricated number

    def test_news_is_refused(self) -> None:
        rep = _refusal_of("اخبار امروز چیست؟")
        assert "«اخبار»" in rep

    def test_both_roads_are_offered(self) -> None:
        rep = _refusal_of("هوا چطوره؟")
        assert "هوش مصنوعی" in rep and "سایت" in rep

    def test_the_question_is_harvested(self) -> None:
        _refusal_of("هوا چطوره؟")
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite.shared_persistent()  # the isolated store (R42)
        q = db.query("SELECT hits FROM unknown_terms WHERE term = 'هوا'")
        rows = q.get("rows", []) if q.get("ok") else []
        assert rows and int(rows[0]["hits"]) >= 1


class TestTheGateIsNarrow:
    def test_a_non_question_about_the_same_topic_stays_free(self) -> None:
        # «قیمت» in an imperative is NOT a knowledge question
        assert answer_reflexive("قیمت را در اکسل بریز") is None

    def test_a_question_with_no_known_topic_stays_free(self) -> None:
        assert answer_reflexive("حال شما چطوره؟") is None  # social, not world-data
