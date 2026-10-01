"""R57 N10 — three real routing gaps found by the night's own measurement.

A 14-command sweep of everyday operator sentences (the N10 discipline: gaps
come from measurement, never from guessing) found three failures, each now
fixed and pinned here:

 1. «سایت example.com را بخوان» was refused with «کدام سایت؟» — a bare
    domain after «سایت» was invisible to the URL extractor, which only knew
    «آدرس X». (The same class as the anchored-regex trap.)
 2. «فایل‌های تکراری در دانلودها» routed to WEBFETCH — the ZWNJ spelling
    matched no vocabulary entry, so the word «دانلود» carried it away.
 3. «چند فرمان اجرا کردی؟» was «نشناختم» — the reflexive class only heard
    «چند تا».
"""

from __future__ import annotations

from universal_mind.persian_params import extract_params
from universal_mind.persian_router import route


class TestBareDomainExtraction:
    def test_a_domain_after_sait_is_found(self) -> None:
        url = extract_params("سایت example.com را بخوان", "webfetch").get("url")
        assert url == "https://example.com"

    def test_a_domain_after_web_or_link_is_found(self) -> None:
        assert extract_params("وب را بگیر example.com", "webfetch")["url"] == "https://example.com"
        out = extract_params("لینک www.aparat.com/watch/x را باز کن", "webfetch")
        assert out["url"] == "https://www.aparat.com/watch/x"

    def test_a_full_url_with_a_query_string_survives(self) -> None:
        out = extract_params("سایت https://x.co/path?q=1&z=2 را بخوان", "webfetch")
        assert out["url"] == "https://x.co/path?q=1&z=2"

    def test_a_dotted_path_url_survives(self) -> None:
        assert extract_params("سایت http://a.ir/b را بخوان", "webfetch")["url"] == "http://a.ir/b"

    def test_a_sentence_without_a_site_still_refuses(self) -> None:
        # the honest refusal is the contract for a sentence with no URL
        assert extract_params("هیچ سایتی نام نبردم", "webfetch") == {}

    def test_a_non_web_command_yields_no_url(self) -> None:
        assert extract_params("نمودار از ۲ و ۳ بکش", "webfetch") == {}


class TestZwnjVocabularyFold:
    def test_a_zwnj_spelled_dedup_command_routes_to_filededupe(self) -> None:
        # the exact sentence from the night's sweep: فایل + ZWNJ + های
        r = route("فایل\u200cهای تکراری در دانلودها را نشان بده")
        assert "filededupe" in r.capabilities
        assert "webfetch" not in r.capabilities  # «دانلود» must NOT win

    def test_the_glued_and_spaced_spellings_still_work(self) -> None:
        assert "filededupe" in route("فایلهای تکراری را نشان بده").capabilities
        assert "filededupe" in route("فایل های تکراری را نشان بده").capabilities

    def test_a_zwnj_spelled_find_command_still_finds_files(self) -> None:
        r = route("فایل\u200cهای بزرگ دیسک D را پیدا کن")
        assert "filesearch" in r.capabilities
        assert "webfetch" not in r.capabilities

    def test_the_fold_does_not_break_plain_commands(self) -> None:
        assert "chart" in route("نمودار از ۲ و ۳ بکش").capabilities
        assert "webfetch" in route("سایت example.com را بخوان").capabilities


class TestRunCountQuestion:
    def test_the_exact_sweep_question_is_reflexive(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        out = answer_reflexive("چند فرمان اجرا کردی؟")
        assert out is not None
        assert "اجرا" in out["agent_report"]

    def test_the_zwnj_spelled_variant_answers_too(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        out = answer_reflexive("تا حالا چند تا فرمان اجرا کرده\u200cای؟")
        assert out is not None
        assert "اجرا" in out["agent_report"]

    def test_the_answer_counts_from_the_real_store(self) -> None:
        from universal_mind.reflexive import answer_reflexive

        out = answer_reflexive("چند فرمان اجرا کردی؟")
        # a REAL store always has the platform's own runs by now — but the
        # shape is the contract: a Persian-digits count line.
        assert out is not None and out["agent_report"].strip()
        assert any(ch in out["agent_report"] for ch in "۰۱۲۳۴۵۶۷۸۹")
