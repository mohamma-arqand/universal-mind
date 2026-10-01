"""The LLM connector — a real chat model behind the Persian command.

R45 item 15: the platform has every real tool EXCEPT a live language
model. This connector speaks the OpenAI-compatible wire format
(POST {base}/chat/completions) against any endpoint the operator wires
via environment — UM_LLM_BASE_URL (e.g. http://127.0.0.1:8000/v1) and
UM_LLM_KEY. The key NEVER lives in the repo; the endpoint is the
operator's own inference server.

Honesty laws (the house style):
- no endpoint configured -> a NAMED refusal, never a silent failure;
- HTTP error -> the error text is surfaced, never swallowed;
- a 200 with a different shape -> the raw payload is named, not guessed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from universal_mind.connectors import Connector, ConnectorResult


class LLMToolConnector(Connector):
    """OpenAI-compatible chat/completions over the operator's endpoint."""

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        base = os.environ.get("UM_LLM_BASE_URL", "").rstrip("/")
        key = os.environ.get("UM_LLM_KEY", "")
        if not base:
            return ConnectorResult(
                ok=False, output=None,
                error=(
                    "مدل زبانی وصل نیست — UM_LLM_BASE_URL را ست کن "
                    "(مثلاً http://127.0.0.1:8000/v1) و UM_LLM_KEY را در محیط بگذار."
                ),
            )
        prompt = str(params.get("prompt", "")).strip()
        if not prompt:
            return ConnectorResult(ok=False, output=None, error="پرامپت خالی است.")
        body = {
            "model": str(params.get("model", os.environ.get("UM_LLM_MODEL", "default"))),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(params.get("max_tokens", 512)),
        }
        req = urllib.request.Request(  # noqa: S310 — the operator's own endpoint
            f"{base}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {key}"} if key else {}),
            },
            method="POST",
        )
        # R57 N7-2 — TRANSIENT-RETRY ON THE WIRE: a first connection to a
        # local test server is sometimes aborted by Windows mid-handshake
        # (WinError 10053 — the very race the R47 wave-1 suite documents).
        # One retry with a short backoff turns that race into a success
        # WITHOUT ever masking a real refusal: an HTTPError (the endpoint
        # answered) and a malformed 200 are returned untouched, and the
        # retry only fires on transport-level failure (URLError/Timeout/
        # ConnectionError/OSError).
        last_exc: Exception | None = None
        payload = None
        http_detail = ""
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=int(params.get("timeout", 60))) as resp:  # noqa: S310
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                # the endpoint ANSWERED — never retried, never masked
                http_detail = exc.read().decode("utf-8", "replace")[:300]
                return ConnectorResult(
                    ok=False, output=None,
                    error=f"مدل خطای HTTP {exc.code} داد: {http_detail}",
                )
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_exc = exc
                if attempt == 0:
                    import time as _t

                    _t.sleep(0.4)  # one short backoff, then one retry
        if payload is None:
            exc = last_exc or RuntimeError("unreachable")
            return ConnectorResult(ok=False, output=None, error=f"ارتباط با مدل نشد: {exc}")
        try:
            text = str(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError):
            return ConnectorResult(
                ok=False, output=None,
                error=f"پاسخ مدل شکلِ شناخته نداشت: {json.dumps(payload)[:300]}",
            )
        return ConnectorResult(ok=True, output={"text": text}, error="")
