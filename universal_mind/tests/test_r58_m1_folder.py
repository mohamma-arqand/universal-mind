"""R58 M1 — «پوشه X را نشان بده» is a DISK listing, not a web read.

Measured gap (the 18-command sweep): «پوشه دانلودها را نشان بده» routed to
WEBFETCH because «دانلود» matched a web keyword and nothing filesearch-shaped
did — the same thief-word class as the ZWNJ dedupe misroute.
"""

from __future__ import annotations

from universal_mind.persian_router import route


class TestFolderShowRoutesToFileSearch:
    def test_the_exact_sweep_command_routes_to_filesearch(self) -> None:
        r = route("پوشه دانلودها را نشان بده")
        assert "filesearch" in r.capabilities
        assert "webfetch" not in r.capabilities

    def test_folder_variants_route_too(self) -> None:
        assert "filesearch" in route("پوشه را نشان بده").capabilities
        assert "filesearch" in route("فولدر را نشان بده").capabilities

    def test_a_folder_command_is_not_a_web_read(self) -> None:
        r = route("پوشه دسکتاپ را نشان بده")
        assert r.capabilities == ("filesearch",) or "webfetch" not in r.capabilities

    def test_web_commands_still_route_to_webfetch(self) -> None:
        # the guard must not swallow the web path
        assert "webfetch" in route("سایت example.com را بخوان").capabilities
        assert "webfetch" in route("صفحه وب news.example.org را بگیر").capabilities

    def test_download_as_a_web_word_still_works_when_it_is_one(self) -> None:
        # «دانلود» in a genuinely web-shaped sentence stays a web command
        r = route("دانلود کن https://example.com/file.zip")
        assert "webfetch" in r.capabilities

    def test_existing_find_commands_are_untouched(self) -> None:
        assert "filesearch" in route("فایل‌های بزرگ دیسک D را پیدا کن").capabilities
        # duplicates go to the DEDUPE tool (the more specific finder), and
        # that is the pre-existing correct route — not filesearch's business
        assert "filededupe" in route("فایلهای تکراری را نشان بده").capabilities
