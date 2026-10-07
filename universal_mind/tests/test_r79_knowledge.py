"""R79 B5 — KNOWLEDGE: the shipped factbook answers before the refusal.

«پایتخت فرانسه چیست؟» was an honest refusal while an offline factbook
can answer the everyday core. Knowledge is the 34th capability: 25+
verified Persian facts with sources, tolerant token matching, a miss
that keeps the honest refusal — never a guess.
"""

from __future__ import annotations



class TestTheKnowledgeCapability:
    def test_a_fact_answers_with_its_source(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("پایتخت فرانسه چیست؟")
        assert p["route"] == ["knowledge"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert "پاریس" in rep and "منبع" in rep

    def test_the_count_shapes_reach_knowledge(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("ایران چند استان دارد؟")
        assert p.get("ok") is True
        assert "۳۱" in str(p.get("agent_report", ""))

    def test_the_speed_of_light_is_knowledge_not_compute(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سرعت نور چند است؟")
        assert p["route"] == ["knowledge"], p["route"]
        assert "۳۰۰" in str(p.get("agent_report", ""))

    def test_math_still_goes_to_compute(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۲۵ بعلاوه ۷ چند میشود؟")
        assert "compute" in (p.get("route") or [])

    def test_a_miss_keeps_the_honest_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کوارک فلان چیه؟")
        assert p.get("ok") is False
        rep = str(p.get("agent_report", ""))
        assert "مدل زبانی" in rep or "حدس" in rep

    def test_the_factbook_is_real_and_clean(self) -> None:
        import json
        from pathlib import Path

        d = json.loads((Path(__file__).resolve().parents[1] / "data" /
                        "facts_fa.json").read_text(encoding="utf-8"))
        assert len(d) >= 20
        for f in d:
            assert f["fact"].endswith(".")
            assert f["keys"], f["fact"][:30]
            assert "source" in f
