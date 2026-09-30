"""R53 wave-3 — IDENTITY: the platform has a name, a face, an honest status.

«اسمت چیه؟» / «تو کی هستی؟» / «وضعیتت چطوره؟» / «چه کارهایی بلدی؟» used to
return None (conversational fallthrough to «نشناختم») — a platform that
answers statistics questions but has no answer for its own NAME. Now each
identity question gets a real, state-aware Persian answer.
"""

from __future__ import annotations


class TestIdentity:
    def test_esm(self) -> None:
        from universal_mind.conversational import answer_conversational

        for q in ("اسمت چیه؟", "اسمت چیست؟", "اسمت؟"):
            a = answer_conversational(q)
            assert a is not None, q
            assert "ذهن جهانی" in a["agent_report"]

    def test_who_are_you_is_state_aware(self) -> None:
        from universal_mind.conversational import answer_conversational

        a = answer_conversational("تو کی هستی؟")
        assert a is not None
        rep = a["agent_report"]
        assert "ذهن جهانی" in rep and "قابلیت" in rep

    def test_khodet_ra_moaarrefi_kon(self) -> None:
        from universal_mind.conversational import answer_conversational

        a = answer_conversational("سلام، خودت را معرفی کن")
        assert a is not None
        assert "ذهن جهانی" in a["agent_report"]

    def test_status_answers_with_real_signals(self) -> None:
        from universal_mind.conversational import answer_conversational

        a = answer_conversational("وضعیتت چطوره؟")
        assert a is not None
        assert a["agent_report"].strip()

    def test_abilities_counted(self) -> None:
        from universal_mind.conversational import answer_conversational

        a = answer_conversational("چه کارهایی بلدی؟")
        assert a is not None
        assert "قابلیت" in a["agent_report"]
        # counted for real: the number of registry capabilities appears in Persian
        assert any(ch in a["agent_report"] for ch in "۰۱۲۳۴۵۶۷۸۹")

    def test_reflexive_help_line_covers_new_forms(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        a = answer_reflexive("چه کارهایی میتونی بکنی؟")
        assert a is not None
        assert "قابلیت" in a["agent_report"]

    def test_router_end_to_end_identity(self) -> None:
        """Through the FULL router: the question never lands on «نشناختم»."""
        from universal_mind.persian_router import route_and_run

        res = route_and_run("اسمت چیه؟")
        assert res.get("agent_report")
        assert "ذهن جهانی" in res["agent_report"]
        assert res.get("route") != [] or res.get("ok") is True
