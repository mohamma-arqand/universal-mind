"""R46 wave 2 — spoken fluency, tested against the LIVE router and a real DB.

Item 5 — the greeting is state-aware (goals, today's runs, by name).
Item 6 — smart retry: «دوباره امتحان کن» reruns the last FAILED run with a
         different strategy and stamps `retry_of` in history.
Item 7 — refusal-sentence stopwords: the refusal itself is never vocabulary;
         the poisoned table is purged and the real subject words survive.
Item 8 — free-form status asks («خب؟ / چی جدید؟») reach the five-signal answer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _fresh_db(monkeypatch: Any, tmp_path: Path) -> DatabaseSuite:
    db = DatabaseSuite(str(tmp_path / "r46w2.db"))
    RunHistory(db)
    monkeypatch.setattr(
        DatabaseSuite, "shared_persistent",
        classmethod(lambda cls: db),
    )
    return db


class TestGreetingIsStateAware:
    def test_bare_greeting_is_short_and_warm(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        r = route_and_run("سلام")
        assert r["ok"] is True
        assert "سلام" in r["agent_report"]

    def test_greeting_knows_today_and_goals(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        route_and_run("نمودار از ۲ و ۳ بکش")
        route_and_run("میانگین ۴ و ۶ را حساب کن")
        from universal_mind.agent_loop import start_goal

        start_goal("هدف: سلامِ داده", ("نمودار از ۲ بکش",))
        n_runs = DatabaseSuite.shared_persistent().query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE date(created_at) = date('now', 'localtime')"
        )["rows"][0]["n"]
        r = route_and_run("سلام")
        fa_n = str(n_runs).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        assert f"{fa_n} فرمان" in r["agent_report"]  # today's runs, the REAL count
        assert "هدف فعال" in r["agent_report"]      # the held goal, by name


class TestSmartRetry:
    def test_retry_reruns_the_last_failed_run_and_stamps_it(
        self, monkeypatch: Any, tmp_path: Path
        ) -> None:
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        # R66-P2 migrated: a dataless chart is a NAMED refusal now — a
        # retry must ride a run that CAN succeed, so the seeded failure
        # carries real data («ستونی» names bar; the numbers are real).
        RunHistory().record("نمودار ستونی از ۳ و ۷ بکش", ["chart"], False,
                            outcome_class="heuristic")
        r = route_and_run("دوباره امتحان کن")
        assert r["ok"] is True
        assert r["agent_report"].startswith("🔁")
        rows = db.query(
            "SELECT id, retry_of, succeeded FROM run_history "
            "ORDER BY id DESC LIMIT 1"
        )["rows"]
        assert rows[0]["retry_of"]                  # the stamp is REAL
        assert rows[0]["succeeded"] == 1            # and the retry SUCCEEDED

    def test_retry_with_no_failure_is_honest(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        r = route_and_run("دوباره امتحان کن")
        assert "شکستی پیدا نکردم" in r["agent_report"]

    def test_retry_of_needs_param_asks_for_the_parameter(
        self, monkeypatch: Any, tmp_path: Path
        ) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        RunHistory().record("نمودار بکش", ["chart"], False,
                            outcome_class="needs_param")
        r = route_and_run("دوباره امتحان کن")
        assert "پارامتر" in r["agent_report"]


class TestRefusalStopwords:
    def test_refusal_sentence_is_never_harvested(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.unknown_harvest import harvest_unknown, top_unknowns

        harvest_unknown(["هیچ قابلیتی شناخته نشد — فرمان اجرا نمیکند"])
        terms = {t["term"] for t in top_unknowns(20)}
        assert not (terms & {"فرمان", "هیچ", "قابلیتی", "ندارد", "نمیکند",
                             "شناخته", "میکند"})

    def test_real_subject_words_are_still_harvested(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.unknown_harvest import harvest_unknown, top_unknowns

        harvest_unknown(["فریبوس مکیدوبالس بده"])
        terms = {t["term"]: t["hits"] for t in top_unknowns(20)}
        assert terms.get("فریبوس") == 1
        assert terms.get("مکیدوبالس") == 1

    def test_purge_cleans_the_poisoned_real_table(self, monkeypatch: Any, tmp_path: Path) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.unknown_harvest import (
            harvest_unknown, purge_refusal_noise, top_unknowns,
        )

        # the poisoned shape, as an OLD row (pre-fix harvest wrote these)
        db = DatabaseSuite.shared_persistent()
        from universal_mind.unknown_harvest import ensure_table

        ensure_table(db)
        db.insert_many("unknown_terms", [
            {"term": "فرمان", "hits": "30"},
            {"term": "قابلیتی", "hits": "27"},
        ])
        harvest_unknown(["کلمهبسیارجدید"])            # a real subject word
        result = purge_refusal_noise()
        assert "فرمان" in result["purged"]
        terms = {t["term"] for t in top_unknowns(20)}
        assert "کلمهبسیارجدید" in terms               # the real word survives
        assert "فرمان" not in terms                    # the noise is gone


class TestFreeFormStatus:
    def test_four_spoken_shapes_reach_the_five_signal_answer(
        self, monkeypatch: Any, tmp_path: Path
        ) -> None:
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        for cmd in ("خب؟", "چی جدید؟", "وضع؟", "خبر چیست؟"):
            r = route_and_run(cmd)
            assert "پنج سیگنال" in r["agent_report"], cmd
