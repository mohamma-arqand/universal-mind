"""The web fetch tool — the SIXTEENTH capability: the platform reaches the web.

urllib (stdlib, no dependencies) with a real User-Agent, honest size limits,
and failure classification. Persian text decodes correctly (charset honored).

Honest rules:
- A fetch returns the REAL status code, the REAL bytes, and the REAL text —
  or the exact classified failure (offline/DNS, HTTP error, timeout, bad
  URL). Nothing is ever fabricated for a failed fetch.
- Only http/https schemes are honored (file:// and friends refused — this is
  a web tool, not a local-file bypass).
- A size cap (default 1MB) prevents runaway reads; truncation is REPORTED.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.content_quarantine import scan_untrusted

_TIMEOUT = 20
_MAX_BYTES = 1_048_576  # 1MB honest cap


class WebFetchTool:
    """A real HTTP fetch: status, bytes, text, title — or the exact failure."""

    name = "webfetch"
    capability = "webfetch"

    def fetch(self, url: str) -> dict[str, Any]:
        if not url.strip():
            return {"ok": False, "error": "empty url", "kind": "bad_url"}
        if not url.lower().startswith(("http://", "https://")):
            return {"ok": False, "error": "only http/https URLs are honored", "kind": "bad_url"}
        req = urllib.request.Request(
            url, headers={"User-Agent": "UniversalMind/1.0 (Windows; +local)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                status = int(resp.status)
                raw = resp.read(_MAX_BYTES + 1)
                truncated = len(raw) > _MAX_BYTES
                if truncated:
                    raw = raw[:_MAX_BYTES]
                charset = resp.headers.get_content_charset() or "utf-8"
                try:
                    text = raw.decode(charset, errors="replace")
                except LookupError:  # unknown charset name
                    text = raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return {
                "ok": False, "kind": "http_error", "status": int(exc.code),
                "error": f"HTTP {exc.code} {exc.reason}",
            }
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, (socket.gaierror, ConnectionError, OSError)):
                return {"ok": False, "kind": "offline", "error": f"unreachable: {reason}"}
            return {"ok": False, "kind": "offline", "error": f"urlopen failed: {reason}"}
        except TimeoutError:
            return {"ok": False, "kind": "timeout", "error": f"timed out after {_TIMEOUT}s"}
        except (ValueError, OSError) as exc:
            return {"ok": False, "kind": "bad_url", "error": str(exc)}

        title = ""
        lower = text[:4000]
        mark = lower.find("<title>")
        if mark >= 0:
            end = lower.find("</title>", mark)
            if end > mark:
                title = lower[mark + 7: end].strip()[:200]
        # R57 THE UNTRUSTED-CONTENT QUARANTINE: whatever this page says, a
        # sentence inside it that LOOKS like an order is data, not a command.
        # We scan the REAL fetched text and report what it tried; the caller
        # keeps the text as data (never routed).
        quarantine = scan_untrusted(text)
        return {
            "ok": True, "status": status, "bytes": len(raw), "chars": len(text),
            "truncated": truncated, "title": title,
            "preview": text[:500], "error": "",
            "quarantine": quarantine.as_dict(),
            "quarantine_summary": quarantine.summary_fa(),
        }


class WebFetchToolConnector:
    """Adapts :class:`WebFetchTool` to the ``Connector`` protocol."""

    def __init__(self, tool: WebFetchTool | None = None) -> None:
        self._tool = tool if tool is not None else WebFetchTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "fetch") or "fetch"
        if operation != "fetch":
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        url = str(params.get("url", "")).strip()
        if not url:
            # Persian with the remedy — the operator asked to summarize a
            # site but named none: which site? (the honest ask, not a
            # bare English error).
            return ConnectorResult(
                ok=False, output=None,
                error="کدام سایت؟ آدرس را بده — مثلا: سایت example.com را بخوان",
            )
        result = self._tool.fetch(url)
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k != "ok"
        })


__all__ = ["WebFetchTool", "WebFetchToolConnector"]