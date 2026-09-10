"""Local OpenAI-compatible stub server — the "real provider" path, offline.

The GATEWAY's :class:`HttpChatProvider` speaks OpenAI's ``/chat/completions``
wire format. This module serves exactly that contract over stdlib HTTP, so the
full stack (MOUTH → decompose → resolve → execute → synthesize → commit) can be
driven by a realistic provider *without leaving the machine* — no API key, no
network address, no external dependency.

The stub is deterministic and safe: it has no side effects, echoes a composed
reply derived from the request, and records each request to a local JSONL file
so the loop's provenance remains audit-ready.

Usage::

    from universal_mind.io.stub_server import StubChatServer

    server = StubChatServer(port=0)      # 0 => ephemeral port
    url = server.start()
    # point HttpChatProvider(base_url=url, model="stub") at it
    server.stop()
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any


def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    """Write a JSON response with the correct content-type."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class _RequestLog:
    """Thread-safe append-only log of the requests the stub served."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._lock = Lock()
        self._path = Path(path) if path else None
        self._records: list[dict[str, Any]] = []
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> str:
        # A deterministic id: file-scoped sequence + request time (approx).
        with self._lock:
            seq = len(self._records) + 1
            self._records.append(record)
            if self._path:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
            return f"req-{seq}"

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records)


class StubChatServer:
    """Serve a deterministic, OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(
        self,
        *,
        port: int = 0,
        model: str = "stub-1",
        log_path: str | Path | None = None,
    ) -> None:
        self._model = model
        self._log = _RequestLog(log_path)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port = port

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("Stub server is not running")
        host, port = self._server.server_address[:2]
        if isinstance(host, bytes):
            host = host.decode("utf-8", errors="replace")
        return f"http://{host}:{port}"

    @property
    def log(self) -> _RequestLog:
        return self._log

    def start(self) -> str:
        """Start serving on a background thread; returns the base URL."""
        handler = self._make_handler()
        self._server = ThreadingHTTPServer(("127.0.0.1", self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        """Shut the server down and join the serving thread."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self
        model = self._model

        class _Handler(BaseHTTPRequestHandler):
            server_version = "UniversalMindStub/1.0"

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8"))
                except ValueError:
                    return {}
                return body if isinstance(body, dict) else {}

            def log_message(self, fmt: str, *args: Any) -> None:  # silence default noise
                pass

            def do_POST(self) -> None:
                if self.path != "/chat/completions":
                    _json(self, 404, {"error": {"message": f"unknown path {self.path}"}})
                    return
                body = self._read_json()
                messages = body.get("messages", [])
                content = server._reply(messages, body.get("model", model))
                server.log.append(
                    {
                        "model": body.get("model", model),
                        "messages": messages,
                        "reply": content,
                        "path": self.path,
                    }
                )
                payload = {
                    "id": "chatcmpl-stub",
                    "object": "chat.completion",
                    "model": body.get("model", model),
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                }
                _json(self, 200, payload)

            def do_GET(self) -> None:
                if self.path in ("/", "/health", "/healthz"):
                    _json(self, 200, {"status": "ok", "model": model})
                    return
                _json(self, 404, {"error": {"message": f"unknown path {self.path}"}})

        return _Handler

    @staticmethod
    def _reply(messages: list[Any], model: str) -> str:
        """Compose a deterministic reply from the message list.

        Uses the last user message's text plus its approximate length, wrapped
        in a stable framing — so identical input always yields identical output
        (the loop stays deterministic) yet the response is *derived* from the
        request rather than a constant echo. If the message carries multimodal
        parts, a short deterministic note about them is appended.
        """
        last_msg = next(
            (m for m in reversed(messages) if isinstance(m, dict) and m.get("role") == "user"),
            {},
        )
        content = last_msg.get("content", "")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        text = str(content)
        base = f"[{model}] received {len(text)} chars: {text}"
        parts = last_msg.get("parts")
        if isinstance(parts, list) and parts:
            kinds = sorted({str(p.get("kind")) for p in parts if isinstance(p, dict)})
            base += f" | parts: {','.join(kinds)}"
        return base