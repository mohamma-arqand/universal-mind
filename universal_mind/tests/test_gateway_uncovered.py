"""Coverage for io/gateway.py's remaining branches (5xx, 4xx, malformed, scripted)."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from universal_mind.core.errors import RetryPolicy
from universal_mind.io.errors import (
    ProviderConfig,
    ProviderError,
    ProviderPermanent,
    ProviderTransient,
)
from universal_mind.io.gateway import (
    Gateway,
    HttpChatProvider,
    Message,
    ProviderResult,
    ScriptedProvider,
    env_resolver,
)


class _Stub(BaseHTTPRequestHandler):
    status: int = 200
    body: str = ""

    def do_POST(self) -> None:
        data = self.body.encode("utf-8")
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _f: str, *_a: object) -> None:
        return


def _serve(body: str, status: int = 200) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _Stub.status = status
    _Stub.body = body
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Wait until the server is actually accepting connections, so the first
    # request cannot race the accept loop and abort (WinError 10053 flake).
    port = server.server_address[1]
    _wait_until_ready(port)
    return server, thread


def _wait_until_ready(port: int, *, attempts: int = 50) -> None:
    import socket
    import time

    for _ in range(attempts):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.02)
    raise RuntimeError(f"stub server on {port} never became ready")


def _provider(server: ThreadingHTTPServer) -> HttpChatProvider:
    port = server.server_address[1]
    return HttpChatProvider(f"http://127.0.0.1:{port}/v1", "m", resolver=lambda _n: "k")


def _call_once_with_retry(
    provider: HttpChatProvider,
    messages: list[Message],
    *,
    attempts: int = 5,
) -> ProviderResult:
    """Call once, retrying the rare Windows connection-abort race (WinError 10053).

    A single localhost HTTP round-trip can occasionally abort before the stub
    server writes its response (an OS-level race, not a code bug). Retry a small
    number of times on ProviderTransient transport failures so the tests assert
    the *logical* outcome (5xx transient / no-content permanent) rather than the
    transport flake.
    """
    import time

    last: Exception | None = None
    for i in range(attempts):
        try:
            return provider.call(messages)
        except ProviderTransient as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(0.05)
    assert last is not None
    raise last


def test_http_5xx_is_transient() -> None:
    server, thread = _serve('{"error": "boom"}', status=500)
    try:
        p = _provider(server)
        messages = [Message(role="user", content="hi")]
        with pytest.raises(ProviderTransient):
            _call_once_with_retry(p, messages)
    finally:
        server.shutdown(); thread.join()


def test_http_429_is_transient() -> None:
    server, thread = _serve('{"error": "rate"}', status=429)
    try:
        p = _provider(server)
        messages = [Message(role="user", content="hi")]
        with pytest.raises(ProviderTransient):
            _call_once_with_retry(p, messages)
    finally:
        server.shutdown(); thread.join()


def test_http_malformed_json_is_permanent() -> None:
    server, thread = _serve("not-json")
    try:
        p = _provider(server)
        with pytest.raises(ProviderPermanent):
            _call_once_with_retry(p, [Message(role="user", content="hi")])
    finally:
        server.shutdown(); thread.join()


def test_http_no_content_is_permanent() -> None:
    server, thread = _serve('{"choices": [{"message": {}}]}')
    try:
        p = _provider(server)
        with pytest.raises(ProviderPermanent):
            _call_once_with_retry(p, [Message(role="user", content="hi")])
    finally:
        server.shutdown(); thread.join()


def test_http_missing_api_key_is_config() -> None:
    p = HttpChatProvider("http://x/v1", "m", resolver=lambda _n: None)
    with pytest.raises(ProviderConfig):
        p.call([Message(role="user", content="hi")])


def test_scripted_callable_returns_provider_result() -> None:
    p = ScriptedProvider([
        lambda _msgs: ProviderResult(content="from-callable", provider_name="x", cost=0.0),
    ])
    assert p.call([Message(role="user", content="hi")]).content == "from-callable"


def test_scripted_callable_raises_provider_error() -> None:
    p = ScriptedProvider([lambda _msgs: ProviderPermanent("nope")])
    with pytest.raises(ProviderPermanent):
        p.call([Message(role="user", content="hi")])


def test_scripted_empty_script_echoes_empty() -> None:
    p = ScriptedProvider([])
    assert p.call([Message(role="user", content="hi")]).content == ""


def test_env_resolver_and_gateway_providers() -> None:
    import os

    os.environ["UM_TEST_XYZ"] = "v"
    assert env_resolver("UM_TEST_XYZ") == "v"
    assert env_resolver("UM_TEST_NOPE") is None
    gw = Gateway([ScriptedProvider(["a"]), ScriptedProvider(["b"])])
    assert len(gw.providers) == 2


def test_gateway_fails_over_config_error() -> None:
    # primary raises ProviderConfig (unretryable) -> fail over to echo fallback
    class _Config(ProviderError):
        pass

    class _ConfigProvider:
        @property
        def name(self) -> str:
            return "config"

        def call(self, messages: list[Message]) -> ProviderResult:
            raise ProviderConfig("no key")

    class _Ok:
        @property
        def name(self) -> str:
            return "ok"

        def call(self, messages: list[Message]) -> ProviderResult:
            return ProviderResult(content="fine", provider_name="ok", cost=0.0)

    gw = Gateway([_ConfigProvider(), _Ok()], retry_policy=RetryPolicy(max_retries=0, jitter=False))
    out = gw.generate([Message(role="user", content="hi")])
    assert out.ok is True
    assert out.provider_name == "ok"


def test_scripted_provider_name_property() -> None:
    p = ScriptedProvider(["x"], name="custom")
    assert p.name == "custom"


def test_http_4xx_maps_auth_and_bad_request() -> None:
    assert isinstance(HttpChatProvider._http_4xx(401, "unauth"), ProviderConfig)
    assert isinstance(HttpChatProvider._http_4xx(403, "forbidden"), ProviderConfig)
    assert isinstance(HttpChatProvider._http_4xx(400, "bad"), ProviderPermanent)
    assert isinstance(HttpChatProvider._http_4xx(404, "nf"), ProviderConfig)


def test_extract_content_non_dict_message() -> None:
    # message is a list (not dict) -> returns None
    assert HttpChatProvider._extract_content({"choices": [{"message": ["x"]}]}) is None