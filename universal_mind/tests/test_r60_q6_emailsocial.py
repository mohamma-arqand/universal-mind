"""R60 Q6 — two misroutes fixed: the email listing and the social answers.

«ایمیل‌هایم را نشان بده» was stolen by CHART (the word «نشان بده» belongs
to chart); «متشکرم» and «حال شما چطوره؟» returned «نشناختم».
"""

from __future__ import annotations

from pathlib import Path

from universal_mind.conversational import answer_conversational
from universal_mind.email_outbox import EmailToolConnector, compose
from universal_mind.persian_params import extract_params
from universal_mind.persian_router import route


class TestRouting:
    def test_the_email_listing_is_email_not_chart(self) -> None:
        r = route("ایمیل‌هایم را نشان بده")
        assert "email" in r.capabilities and "chart" not in r.capabilities

    def test_sent_emails_shape_routes_too(self) -> None:
        assert "email" in route("ایمیل‌های ارسالی را نشان بده").capabilities

    def test_the_compose_shape_is_untouched(self) -> None:
        assert route("به مدیر ایمیل بزن").capabilities == ("email",)


class TestParams:
    def test_the_listing_shape_yields_operation_list(self) -> None:
        assert extract_params("ایمیل‌هایم را نشان بده", "email") == {
            "operation": "list"}

    def test_the_compose_shape_yields_compose(self) -> None:
        p = extract_params("به مدیر ایمیل بزن", "email")
        assert p.get("operation", "compose") == "compose"


class TestConnectorList:
    def test_an_empty_outbox_is_honest(self, tmp_path: Path) -> None:
        res = EmailToolConnector(out_dir=str(tmp_path)).connect(
            {}, {"operation": "list"})
        assert res.ok is True
        assert res.output["count"] == 0 and res.output["emails"] == []

    def test_a_real_email_is_listed_with_its_subject(self, tmp_path: Path) -> None:
        compose(to="ali@example.com", subject="گواه ر۶۰", body="hi",
                out_dir=str(tmp_path))
        res = EmailToolConnector(out_dir=str(tmp_path)).connect(
            {}, {"operation": "list"})
        assert res.ok is True
        assert res.output["count"] == 1
        assert res.output["emails"][0]["subject"] == "گواه ر۶۰"
        assert res.output["emails"][0]["to"] == "ali@example.com"

    def test_a_mime_subject_is_decoded_not_base64_soup(self, tmp_path: Path) -> None:
        # Persian subjects are stored MIME-encoded (=?utf-8?b?...?=) — the
        # listing must DECODE them or the operator sees base64 soup.
        compose(to="a@b.c", subject="گزارش ذهن یکپارچه", body="x",
                out_dir=str(tmp_path))
        res = EmailToolConnector(out_dir=str(tmp_path)).connect(
            {}, {"operation": "list"})
        subj = res.output["emails"][0]["subject"]
        assert subj == "گزارش ذهن یکپارچه" and "=?" not in subj


class TestSocialAnswers:
    def test_moteshakeram_is_answered(self) -> None:
        ans = answer_conversational("متشکرم")
        assert ans is not None and "خواهش" in ans["agent_report"]

    def test_tashakor_is_answered(self) -> None:
        assert answer_conversational("تشکر") is not None

    def test_the_mood_question_is_answered_honestly(self) -> None:
        ans = answer_conversational("حال شما چطوره؟")
        assert ans is not None
        assert "سالم و آماده" in ans["agent_report"]  # no fake feelings

    def test_the_old_thanks_words_still_answer(self) -> None:
        for word in ("ممنون", "مرسی", "سپاس"):
            assert answer_conversational(word) is not None, word
