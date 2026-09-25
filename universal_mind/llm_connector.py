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
        try:
            with urllib.request.urlopen(req, timeout=int(params.get("timeout", 60))) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            return ConnectorResult(ok=False, output=None,
                                   error=f"مدل خطای HTTP {exc.code} داد: {detail}")
        except Exception as exc:  # noqa: BLE001 — the wire's own error, surfaced
            return ConnectorResult(ok=False, output=None, error=f"ارتباط با مدل نشد: {exc}")
        try:
            text = str(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError):
            return ConnectorResult(
                ok=False, output=None,
                error=f"پاسخ مدل شکلِ شناخته نداشت: {json.dumps(payload)[:300]}",
            )
        return ConnectorResult(ok=True, output={"text": text}, error="")
