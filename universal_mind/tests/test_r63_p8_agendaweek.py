"""R63 P8 — «برنامه هفته آینده من چیست؟» is the AGENDA, not an LLM
question.

The sweep measured the sentence falling to the live-model refusal —
but appointments are the platform's OWN data. The agenda words now
carry the week-shaped questions; the answer lists the real reminders.
"""

from __future__ import annotations


class TestTheAgendaWords:
    def test_the_week_question_reaches_the_agenda(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("برنامه هفته آینده من چیست؟")
        assert p["ok"] is True
        assert p["route"] == ["reflexive"]
        rep = p["agent_report"]
        # the AGENDA answered — its real headline, empty or full,
        # never the LLM refusal.
        assert ("برنامه" in rep or "قرار" in rep)
        assert "پرسش دانشی" not in rep and "مدل زبانی" not in rep

    def test_the_zwnj_spelling_works_too(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("برنامه هفتهٔ آینده من چیست؟")
        assert p["route"] == ["reflexive"]

    def test_the_older_agenda_shapes_still_answer(self) -> None:
        from universal_mind.persian_router import route_and_run

        for cmd in ("قرارهایم را نشان بده", "برنامه‌ام را نشان بده"):
            p = route_and_run(cmd)
            assert p["route"] == ["reflexive"], cmd
            rep = p["agent_report"]
            assert ("برنامه" in rep or "قرار" in rep), cmd
            assert "مدل زبانی" not in rep, cmd
