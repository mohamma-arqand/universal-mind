"""R79 B3 — TRANSLATE: a real offline capability, honestly bounded.

The audit's biggest category gap: «ترجمه» was mapped to webfetch (site
reading!) and the greeting gate swallowed «سلام رو به انگلیسی ترجمه کن».
Now translate is its own capability: a compact real frequency dictionary
ships as data (universal_mind/data/dict_fa_en.json), the direction is
decided by the SCRIPT of the text (Persian → English, Latin → Persian),
found words translate, missing words are NAMED — never a guessed
translation, never silence.
"""

from __future__ import annotations



class TestTheTranslateCapability:
    def test_a_translation_is_work_not_a_greeting(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سلام رو به انگلیسی ترجمه کن")
        assert p["route"] == ["translate"], p["route"]
        assert "hello" in str(p.get("agent_report", ""))

    def test_fa_to_en_and_en_to_fa(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("«کتاب» را به انگلیسی ترجمه کن")
        assert "book" in str(p.get("agent_report", ""))
        p2 = route_and_run("water را به فارسی ترجمه کن")
        assert "آب" in str(p2.get("agent_report", ""))

    def test_the_script_decides_the_direction(self) -> None:
        from universal_mind.persian_router import route_and_run

        # Persian text + «به فارسی» in the ask: the word is PERSIAN, so it
        # must still translate TO ENGLISH (the script decides, not the ask).
        p = route_and_run("«برنامه» را به فارسی ترجمه کن")
        assert "program" in str(p.get("agent_report", ""))

    def test_an_unknown_word_is_a_named_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("«زلمزلمزو» را به انگلیسی ترجمه کن")
        assert p["ok"] is False
        rep = str(p.get("agent_report", ""))
        assert "واژهنامه" in rep and "نمیسازم" in rep

    def test_the_plain_greeting_survives(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سلام")
        assert p["route"] == ["conversational"], p["route"]

    def test_the_pocket_dictionary_is_real_data(self) -> None:
        from pathlib import Path

        import json

        d = json.loads((Path(__file__).resolve().parents[1] / "data" /
                        "dict_fa_en.json").read_text(encoding="utf-8"))
        assert d["fa2en"]["سلام"] == "hello"
        assert d["en2fa"]["water"] == "آب"
        assert len(d["fa2en"]) >= 100
