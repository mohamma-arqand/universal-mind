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
- R57 THE SSRF GUARD: a target on the operator's OWN machine or network is
  refused by default. The platform must not be talked into reading
  http://127.0.0.1/... , http://10.x , http://192.168.x , the cloud metadata
  address 169.254.169.254, or anything a redirect tries to send it to.
  A LOCAL read is an explicit act: pass ``allow_private=True`` — and a
  redirect can NEVER lift the guard, it can only be refused.
- R57 THE UNTRUSTED-CONTENT QUARANTINE: whatever a page says, a sentence
  inside it that LOOKS like an order is DATA, never a command.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.content_quarantine import scan_untrusted

_TIMEOUT = 20
_MAX_BYTES = 1_048_576  # 1MB honest cap
_SAFE_SCHEMES = ("http://", "https://")

# names that always mean "this machine", never a public site
_BLOCKED_HOSTNAMES = frozenset({
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata", "metadata.google.internal",
})
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")

_BLOCKED_TARGET_FA = (
    "این آدرس داخلی/خصوصی است و به‌طور پیش‌فرض خوانده نمی‌شود — "
    "اگر واقعاً می‌خواهی سرویسِ روی همین دستگاه را بخوانی، صریح بگو «آدرس داخلی مجاز است»"
)


class _BlockedTarget(Exception):
    """A target we refuse to contact (private host, or a redirect to one)."""


def _host_of(url: str) -> str:
    """The hostname of a URL, lowercased — '' when it cannot be parsed."""
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _is_private_target(url: str) -> bool:
    """True for loopback / private / link-local / reserved / metadata targets.

    A URL whose host cannot be parsed is treated as unsafe: an address this
    tool cannot reason about is not an address it will contact.
    """
    host = _host_of(url)
    if not host:
        return True
    if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a real public name — resolve normally
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect may not leave http/https, nor reach a private address."""

    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Any:
        scheme = urllib.parse.urlsplit(newurl).scheme.lower()
        if scheme not in ("http", "https"):
            raise _BlockedTarget(
                f"ریدایرکت به اسکیمِ {scheme or 'ناشناس'} رد شد (فقط http/https)"
            )
        if _is_private_target(newurl):
            raise _BlockedTarget(_BLOCKED_TARGET_FA)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# ONE opener, guarded. Tests may replace ``_OPENER`` to stub the transport.
_OPENER = urllib.request.build_opener(_GuardedRedirect())


class WebFetchTool:
    """A real HTTP fetch: status, bytes, text, title — or the exact failure."""

    name = "webfetch"
    capability = "webfetch"

    def fetch(self, url: str, allow_private: bool = False) -> dict[str, Any]:
        url = url.strip()
        if not url:
            return {"ok": False, "error": "empty url", "kind": "bad_url"}
        if not url.lower().startswith(_SAFE_SCHEMES):
            return {"ok": False, "error": "only http/https URLs are honored", "kind": "bad_url"}
        if not allow_private and _is_private_target(url):
            return {"ok": False, "kind": "blocked_target", "error": _BLOCKED_TARGET_FA}

        req = urllib.request.Request(
            url, headers={"User-Agent": "UniversalMind/1.0 (Windows; +local)"}
        )
        try:
            with _OPENER.open(req, timeout=_TIMEOUT) as resp:
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
        except _BlockedTarget as exc:
            return {"ok": False, "kind": "blocked_target", "error": str(exc)}
        except urllib.error.HTTPError as exc:
            # A redirect that surfaces as an HTTPError is a redirect urllib
            # REFUSED to follow (a scheme it will not honour — file:// and
            # friends). Reporting that as a raw "HTTP 302" would hide the
            # real event: a redirect we blocked on purpose.
            if int(exc.code) in (301, 302, 303, 307, 308):
                return {
                    "ok": False, "kind": "blocked_target",
                    "error": "ریدایرکت به مقصدی که مجاز نیست رد شد — از خواندن آن صرف‌نظر شد.",
                }
            return {
                "ok": False, "kind": "http_error", "status": int(exc.code),
                "error": f"HTTP {exc.code} {exc.reason}",
            }
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, _BlockedTarget):
                return {"ok": False, "kind": "blocked_target", "error": str(reason)}
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
        result = self._tool.fetch(url, allow_private=bool(params.get("allow_private", False)))
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k != "ok"
        })


__all__ = ["WebFetchTool", "WebFetchToolConnector"]