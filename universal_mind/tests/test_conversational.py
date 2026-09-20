"""Tests: the conversational class + the navigation holes it closed."""

from __future__ import annotations


class TestConversational:
    def test_greeting_gets_an_answer(self) -> None:
        """«سلام» is the FIRST word anyone says — silence is a broken face."""
        from universal_mind.persian_router import route_and_run

        p = route_and_run("سلام")
        assert p["route"] == ["conversational"]
        assert "سلام" in p["agent_report"] and "فرمان" in p["agent_report"] or "کار" in p["agent_report"]

    def test_thanks_and_greetings_variants(self) -> None:
        from universal_mind.persian_router import route_and_run

        for c in ("خسته نباشید", "ممنون", "مرسی"):
            p = route_and_run(c)
            assert p["route"] == ["conversational"], c
            assert len(p["agent_report"]) > 3

    def test_whats_up_reads_real_state(self) -> None:
        """«دنبال چه میگردی؟» answers with the LAST REAL work, not a guess."""
        from universal_mind.persian_router import route_and_run

        p = route_and_run("دنبال چه میگردی؟")
        assert p["route"] == ["conversational"]
        assert "خدمت" in p["agent_report"]

    def test_help_names_real_commands(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("کمک کن لطفا")
        assert p["route"] == ["conversational"]
        assert "نمودار" in p["agent_report"]  # real example commands

    def test_real_commands_never_hijacked(self) -> None:
        """Small talk never steals a genuine command."""
        from universal_mind.persian_router import route_and_run

        assert route_and_run("میانگین ۳ و ۹ را حساب کن")["route"] != ["conversational"]
        assert route_and_run("نمودار خطی بساز")["route"] != ["conversational"]


class TestNavigationHolesClosed:
    def test_analysis_routes_to_data(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "data" in route_and_run("دادههای فروش را تحلیل کن")["route"]

    def test_zip_colloquial(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "archive" in route_and_run("فایلها را زیپ کن")["route"]

    def test_reminder_colloquial(self) -> None:
        from universal_mind.persian_router import route_and_run

        assert "notify" in route_and_run("زمان بگیر که فردا صبح ۸ یادم بندی")["route"]

    def test_yesterday_reflex(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چیزی که دیروز ساختی رو نشونم بده")
        assert p["route"] == ["reflexive"]
        assert "آخرین کار" in p["agent_report"]

    def test_trend_reflex_real_numbers(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("ترندها رو نشون بده")
        assert p["route"] == ["reflexive"]
        assert ("روند" in p["agent_report"]) or ("دادهی روندی" in p["agent_report"])

    def test_pdf_from_results_is_a_real_document(self) -> None:
        """«یک فایل PDF از نتایج بساز» — a REAL pdf lands on disk."""
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یک فایل PDF از نتایج بساز")
        assert "pdf" in p["route"]
        assert p["ok"] is True
        path = (p.get("result") or {}).get("pdf", {}).get("path", "")
        assert path and path.lower().endswith(".pdf")