"""Tests: the web fetch tool (16th capability) — real HTTP or the exact failure."""

from __future__ import annotations


class TestWebFetchTool:
    def test_a_real_page_comes_back_real(self) -> None:
        """example.com: status 200, real bytes, the real title — live fetch."""
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("https://example.com")
        assert result["ok"] is True
        assert result["status"] == 200
        assert result["bytes"] > 500
        assert "Example" in result["title"]

    def test_offline_is_classified_not_crashed(self) -> None:
        """A nonexistent host: classified 'offline', never an exception."""
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("https://nonexistent-host-zz9.example.invalid")
        assert result["ok"] is False
        assert result["kind"] in ("offline", "timeout")
        assert result["error"]

    def test_non_http_scheme_is_refused(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("file:///C:/Windows/win.ini")
        assert result["ok"] is False
        assert result["kind"] == "bad_url"

    def test_empty_url_refused(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("   ")
        assert result["ok"] is False

    def test_connector_contracts(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.webfetch_tool import WebFetchToolConnector

        conn = WebFetchToolConnector()
        no_url = conn.connect({}, {"operation": "fetch"})
        assert isinstance(no_url, ConnectorResult) and no_url.ok is False
        bad_op = conn.connect({}, {"operation": "post"})
        assert bad_op.ok is False


class TestWebFetchPersian:
    def test_url_extraction_from_the_sentence(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("صفحه وب https://example.com را بگیر", "webfetch")
        assert params["url"] == "https://example.com"

    def test_bare_domain_gets_https(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("آدرس example.com را بگیر", "webfetch")
        assert params["url"] == "https://example.com"

    def test_no_url_is_refused_not_guessed(self) -> None:
        from universal_mind.persian_params import extract_params

        params = extract_params("یک سایت را بگیر", "webfetch")
        assert params == {}  # honest: nothing recognizable, never a guess
