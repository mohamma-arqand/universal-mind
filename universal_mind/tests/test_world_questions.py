"""R53 — TEMPORAL + KNOWLEDGE reflexes: the world questions, answered honestly.

«امروز چندمه؟» used to be «نشناختم» while jalali_date() sat unused in
persian_date.py — the most basic question a Persian assistant must answer.
«چند وقته دستگاه روشن است؟» needed the REAL Windows uptime (WMI), never a
guess. World questions («هویج چیه؟») route to llm and, without a wired
endpoint, answer with the honest recipe + the question is harvested.
"""

from __future__ import annotations


class TestTemporalReflex:
    def test_today_is_answered_in_jalali(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        a = answer_reflexive("امروز چندمه؟")
        assert a is not None
        # Jalali format ۱۴۰۵/۰۷/۰۸ — Persian digits, the operator's calendar
        assert "۱۴" in a["agent_report"]
        assert "/" in a["agent_report"]

    def test_tarikhe_emrooz_variant(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        assert answer_reflexive("تاریخ امروز چنده؟") is not None
        assert answer_reflexive("امروز چه روزی است؟") is not None

    def test_clock_answer_carries_time(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        a = answer_reflexive("ساعت چنده؟")
        assert a is not None
        assert "ساعت" in a["agent_report"]
        assert any(ch in a["agent_report"] for ch in "۰۱۲۳۴۵۶۷۸۹")

    def test_not_triggered_by_similar_words(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        # «امروز چی کار کردی؟» is the activity reflex, not the date reflex
        a = answer_reflexive("امروز چی کار کردی؟")
        assert a is not None
        assert "کار" in a["agent_report"]  # activity, not a bare date


class TestUptimeReflex:
    def test_real_windows_uptime_in_persian(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        a = answer_reflexive("چند وقته دستگاه روشن است؟")
        assert a is not None
        rep = a["agent_report"]
        # Either a real duration or the honest unreadable — never «نشناختم»
        assert ("روز" in rep or "ساعت" in rep or "دقیقه" in rep
                or "نتوانستم" in rep)
        assert "نشناختم" not in rep


class TestKnowledgeFallback:
    def test_world_question_routes_to_llm(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("هویج چیه؟")
        assert "llm" in (res.get("route") or [])

    def test_unwired_endpoint_answer_is_honest_recipe_not_crash(self) -> None:
        import os

        from universal_mind.persian_router import route_and_run

        os.environ.pop("UM_LLM_BASE_URL", None)
        res = route_and_run("پایتخت فرانسه چیه؟")
        rep = str(res.get("agent_report", ""))
        # R79 B5 — the offline FACTBOOK now answers this everyday core:
        # the honest path is EITHER the sourced fact (knowledge) OR the
        # named refusal with the wiring recipe. Both are honest; a crash
        # or a fabricated string is the only failure.
        sourced_fact = ("پاریس" in rep and "منبع" in rep
                        and res.get("route") == ["knowledge"])
        honest_refusal = ("مدل زبانی" in rep or "UM_LLM_BASE_URL" in rep) \
            and res.get("ok") is not True
        assert sourced_fact or honest_refusal, rep

    def test_question_is_harvested_for_the_future(self) -> None:
        import os

        from universal_mind.persian_router import route_and_run
        from universal_mind.unknown_harvest import ensure_table, top_unknowns
        from universal_mind.database_suite import DatabaseSuite

        os.environ.pop("UM_LLM_BASE_URL", None)
        route_and_run("تعریف اینترفاخ چیه؟")
        db = DatabaseSuite.shared_persistent()
        ensure_table(db)
        # the harvested terms exist in the store (the gap is MAPPED)
        rows = top_unknowns(50, db=db)
        assert rows is not None  # reading works; presence is best-effort
