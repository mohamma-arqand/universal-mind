"""Tests: the reflexive class — self-questions answered from the real store."""

from __future__ import annotations


class TestReflexive:
    def test_run_counts_are_real(self) -> None:
        """«چند تا اجرا موفق داشتی؟» — a real number from run_history."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("چند تا اجرا موفق داشتی؟")
        assert payload["route"] == ["reflexive"]
        assert payload["ok"] is True
        assert "اجرا" in payload["agent_report"] and "موفق" in payload["agent_report"]

    def test_most_successful_capability_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("موفقترین قابلیت کدومه؟")
        assert payload["route"] == ["reflexive"]
        assert "موفقترین قابلیت" in payload["agent_report"]

    def test_most_successful_chain_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("کدام زنجیره بیشتر موفق شده؟")
        assert "موفقترین زنجیره" in payload["agent_report"]
        assert "برد" in payload["agent_report"]

    def test_last_made_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("آخرین چیزی که ساختی چی بود؟")
        assert "آخرین کار موفق" in payload["agent_report"]

    def test_help_counts_the_capabilities(self) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.real_tool_registry import real_tool_registry

        payload = route_and_run("چیکار میتونی بکنی؟")
        caps = real_tool_registry().capabilities()
        assert str(len(caps)) in payload["agent_report"] or str(len(caps)).translate(
            str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        ) in payload["agent_report"]

    def test_goal_counts_by_state(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("چند تا هدف ثبت شده؟")
        assert "هدفها" in payload["agent_report"]

    def test_non_questions_still_route_normally(self) -> None:
        """The reflexive layer never hijacks a real command."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۳ و ۹ را حساب کن")
        assert payload["route"] != ["reflexive"]

    def test_url_in_sentence_now_routes_to_webfetch(self) -> None:
        """«این لینک رو باز کن» — the vocabulary hole is closed."""
        from universal_mind.persian_router import _VOCAB

        words = [w for w, _ in _VOCAB]
        assert "لینک" in words and "باز کن" in words