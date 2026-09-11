"""Real external tools — a genuine service behind the gateway, fail-safe.

A mind is only "capable" if it can actually reach out and do real work. This
module is the real-tool layer: a :class:`RealToolProvider` that issues a real
HTTP call to a local, deterministic tool service (an arithmetic / echo service
served over the same stdlib HTTP the stub uses) and fails safe to a fallback
when the service is unreachable — so "capable" never means "crashes when the
network is down".

Deterministic and local: the tool service is self-hosted on an ephemeral port.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Result of a real-tool call."""

    ok: bool
    output: Any
    via_fallback: bool          # True if the real tool was unreachable and we fell back
    note: str


class ToolService:
    """A tiny self-hosted tool endpoint (arithmetic) — the "real" backend."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._url: str | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        """The running service's base URL (raises before start)."""
        if self._url is None:
            raise RuntimeError("ToolService is not running")
        return self._url

    def start(self) -> str:
        """Start a background HTTP tool service; returns its base URL."""
        def _reply(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
            data = json.dumps(payload).encode("utf-8")
            handler.send_response(status)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)

        host, port = self._host, self._port

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                if self.path.startswith("/compute?"):
                    import urllib.parse

                    qs = urllib.parse.parse_qs(self.path.split("?", 1)[1])
                    op = qs.get("op", ["sum"])[0]
                    args = [float(x) for x in qs.get("args", [""])[0].split(",") if x]
                    if op == "sum":
                        result = float(sum(args))
                    elif op == "product" and args:
                        result = 1.0
                        for a in args:
                            result *= a
                    else:
                        result = 0.0
                    _reply(self, {"result": result})
                    return
                if self.path in ("/", "/health"):
                    _reply(self, {"status": "ok"})
                    return
                _reply(self, {"error": "not found"}, status=404)

        self._server = ThreadingHTTPServer((host, port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        assert self._server is not None
        self._url = f"http://{self._host}:{self._server.server_address[1]}"
        return self._url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None


class RealToolProvider:
    """Call a real tool service via HTTP, failing safe to a fallback."""

    def __init__(self, base_url: str, *, fallback: Callable[[str], Any] | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._fallback = fallback if fallback is not None else (lambda _: "fallback")

    def compute(self, op: str, args: list[float]) -> ToolResult:
        """Call the tool's ``/compute``; on any error, return the fallback."""
        query = ",".join(str(a) for a in args)
        url = f"{self._base_url}/compute?op={op}&args={query}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
            return ToolResult(ok=True, output=body.get("result"), via_fallback=False, note="real tool")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            fb = self._fallback(f"{op}:{query}")
            return ToolResult(ok=True, output=fb, via_fallback=True, note=f"fallback after {exc!r}")