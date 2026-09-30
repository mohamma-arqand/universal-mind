"""R57 N1 — THE SSRF GUARD, pinned.

The platform must not be talked into reading the operator's own machine or
network: loopback, private ranges, link-local (cloud metadata), reserved,
plus the names that mean "this machine". A local read is an EXPLICIT act
(``allow_private=True``) and a redirect can never lift the guard.
"""

from __future__ import annotations

import urllib.error

import pytest

from universal_mind.webfetch_tool import (
    WebFetchTool,
    WebFetchToolConnector,
    _GuardedRedirect,
    _host_of,
    _is_private_target,
)

_PRIVATE_URLS = [
    "http://127.0.0.1/",
    "http://127.0.0.1:8080/health",
    "http://localhost/",
    "http://localhost:5000/",
    "http://LOCALHOST/x",
    "http://10.0.0.1/",
    "http://10.255.255.254/admin",
    "http://192.168.1.1/",
    "http://172.16.5.4/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://0.0.0.0/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://nas.local/",
    "http://printer.internal/",
]

_PUBLIC_URLS = [
    "https://example.com/",
    "http://example.com/path?q=1",
    "https://8.8.8.8/",
    "https://sub.domain.example.org/page",
]


class TestPrivateDetection:
    @pytest.mark.parametrize("url", _PRIVATE_URLS)
    def test_private_targets_are_recognized(self, url: str) -> None:
        assert _is_private_target(url) is True

    @pytest.mark.parametrize("url", _PUBLIC_URLS)
    def test_public_targets_are_not_flagged(self, url: str) -> None:
        assert _is_private_target(url) is False

    def test_an_unparseable_host_is_unsafe(self) -> None:
        # an address the tool cannot reason about is not one it will contact
        assert _is_private_target("http://") is True
        assert _is_private_target("https://:80/") is True

    def test_host_parsing_handles_port_and_userinfo(self) -> None:
        assert _host_of("http://user:pw@example.com:8080/x") == "example.com"
        assert _host_of("http://[::1]:9000/") == "::1"


class TestFetchRefusesPrivate:
    @pytest.mark.parametrize("url", _PRIVATE_URLS)
    def test_private_fetch_is_refused_by_default(self, url: str) -> None:
        r = WebFetchTool().fetch(url)
        assert r["ok"] is False
        assert r["kind"] == "blocked_target"
        assert r["error"]
        assert "preview" not in r  # no content, no fabrication

    def test_the_refusal_carries_the_persian_remedy(self) -> None:
        r = WebFetchTool().fetch("http://127.0.0.1:9/")
        assert "آدرس داخلی مجاز است" in r["error"]

    def test_the_refusal_happens_before_any_connection(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """The guard must not dial the number first and apologise later."""
        import universal_mind.webfetch_tool as wf

        def _boom(*a: object, **k: object) -> object:
            raise AssertionError("the tool connected to a blocked target")

        monkeypatch.setattr(wf._OPENER, "open", _boom)
        r = wf.WebFetchTool().fetch("http://169.254.169.254/latest/meta-data/")
        assert r["kind"] == "blocked_target"


class TestConnectorHonoursTheFlag:
    def test_connector_blocks_by_default(self) -> None:
        out = WebFetchToolConnector().connect({}, {"url": "http://127.0.0.1:9/x"})
        assert out.ok is False
        assert "داخلی" in str(out.error)

    def test_connector_passes_allow_private_through(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import universal_mind.webfetch_tool as wf

        seen: dict[str, object] = {}

        class _Fake(wf.WebFetchTool):
            def fetch(self, url: str, allow_private: bool = False) -> dict[str, object]:
                seen["url"] = url
                seen["allow_private"] = allow_private
                return {"ok": True, "chars": 1}

        r = wf.WebFetchToolConnector(_Fake()).connect(
            {}, {"url": "http://127.0.0.1:9/x", "allow_private": True}
        )
        assert r.ok is True
        assert seen["allow_private"] is True


class TestRedirectGuard:
    def _handler(self) -> _GuardedRedirect:
        return _GuardedRedirect()

    def test_redirect_to_file_scheme_is_refused(self) -> None:
        with pytest.raises(Exception) as exc:
            self._handler().redirect_request(
                None, None, 302, "Found", {}, "file:///C:/Windows/win.ini"
            )
        assert "file" in str(exc.value)

    def test_redirect_to_a_private_host_is_refused(self) -> None:
        with pytest.raises(Exception) as exc:
            self._handler().redirect_request(
                None, None, 302, "Found", {}, "http://169.254.169.254/latest/"
            )
        assert "داخلی" in str(exc.value) or "private" in str(exc.value).lower()

    def test_redirect_to_a_public_https_target_is_allowed_through(self) -> None:
        # a normal redirect must still work — the guard is not a wall
        import urllib.request

        req = urllib.request.Request("http://example.com/a")
        out = self._handler().redirect_request(
            req, None, 302, "Found", {}, "https://example.com/b"
        )
        assert out is not None

    def test_a_blocked_redirect_surfaces_as_blocked_target(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """The refusal type must survive urllib's wrapping."""
        import universal_mind.webfetch_tool as wf

        def _raise(*a: object, **k: object) -> object:
            raise urllib.error.URLError(wf._BlockedTarget("nope"))

        monkeypatch.setattr(wf._OPENER, "open", _raise)
        r = wf.WebFetchTool().fetch("https://example.com/redirects-me")
        assert r["kind"] == "blocked_target"


class TestRedirectClassification:
    """A redirect urllib refused is a BLOCKED TARGET, not a raw HTTP error."""

    def test_a_refused_redirect_is_classified_blocked(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import urllib.error

        import universal_mind.webfetch_tool as wf

        def _raise(*a: object, **k: object) -> object:
            raise urllib.error.HTTPError(
                "https://example.com/", 302,
                "Found - Redirection to url 'file:///x' is not allowed", {}, None,  # type: ignore[arg-type]
            )

        monkeypatch.setattr(wf._OPENER, "open", _raise)
        r = wf.WebFetchTool().fetch("https://example.com/")
        assert r["kind"] == "blocked_target"
        assert "ریدایرکت" in r["error"]

    def test_a_real_http_error_is_still_an_http_error(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import urllib.error

        import universal_mind.webfetch_tool as wf

        def _raise(*a: object, **k: object) -> object:
            raise urllib.error.HTTPError(
                "https://example.com/", 404, "Not Found", {}, None,  # type: ignore[arg-type]
            )

        monkeypatch.setattr(wf._OPENER, "open", _raise)
        r = wf.WebFetchTool().fetch("https://example.com/")
        assert r["kind"] == "http_error"
        assert r["status"] == 404


class TestNoRegression:
    def test_empty_and_bad_scheme_still_classified(self) -> None:
        assert WebFetchTool().fetch("")["kind"] == "bad_url"
        assert WebFetchTool().fetch("file:///etc/passwd")["kind"] == "bad_url"
        assert WebFetchTool().fetch("ftp://example.com/")["kind"] == "bad_url"

    def test_a_public_target_is_not_screened_as_private(self) -> None:
        # it will fail on the network, but it must fail as offline/timeout —
        # never as blocked_target (that would be a false accusation)
        r = WebFetchTool().fetch("https://dead-host-zz9.example.invalid")
        assert r["ok"] is False
        assert r["kind"] in ("offline", "timeout")
