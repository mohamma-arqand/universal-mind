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
    return server, thread


def _provider(server: ThreadingHTTPServer) -> HttpChatProvider:
    port = server.server_address[1]
    return HttpChatProvider(f"http://127.0.0.1:{port}/v1", "m", resolver=lambda _n: "k")


def test_http_5xx_is_transient() -> None:
    server, thread = _serve('{"error": "boom"}', status=500)
    try:
        p = _provider(server)
        with pytest.raises(ProviderTransient):
            p.call([Message(role="user", content="hi")])
    finally:
        server.shutdown(); thread.join()


def test_http_429_is_transient() -> None:
    server, thread = _serve('{"error": "rate"}', status=429)
    try:
        p = _provider(server)
        with pytest.raises(ProviderTransient):
            p.call([Message(role="user", content="hi")])
    finally:
        server.shutdown(); thread.join()


def test_http_malformed_json_is_permanent() -> None:
    server, thread = _serve("not-json")
    try:
        p = _provider(server)
        with pytest.raises(ProviderPermanent):
            p.call([Message(role="user", content="hi")])
    finally:
        server.shutdown(); thread.join()


def test_http_no_content_is_permanent() -> None:
    server, thread = _serve('{"choices": [{"message": {}}]}')
    try:
        p = _provider(server)
        with pytest.raises(ProviderPermanent):
            p.call([Message(role="user", content="hi")])
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