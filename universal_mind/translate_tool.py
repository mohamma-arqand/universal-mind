"""R79 B3 — TRANSLATE: a real offline Persian↔English pocket dictionary.

The audit's biggest remaining gap: «ترجمه» was mapped to webfetch (read a
site!) and drowned behind the greeting gate. Translation is a real,
everyday need — and an offline machine must still do the everyday core
of it: common words and phrases both ways, with an honest NAMED refusal
for what the pocket does not hold (no guessed translation, ever).

The wordlist is a real compact frequency dictionary (Persian top words
with their English glosses). It ships as data, not a network call.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_DATA = Path(__file__).resolve().parent / "data" / "dict_fa_en.json"
_lock = threading.Lock()
_cache: dict[str, dict[str, str]] | None = None


def _load() -> dict[str, dict[str, str]]:
    global _cache
    with _lock:
        if _cache is None:
            try:
                _cache = json.loads(_DATA.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                _cache = {"fa2en": {}, "en2fa": {}}
        return _cache


def _normalize_fa(s: str) -> str:
    return (s.replace("ی", "ی").replace("ك", "ک")
             .replace("\u200c", " ").strip())


def translate(text: str, to_english: bool = True) -> dict[str, Any]:
    """Translate a SHORT phrase with the offline pocket dictionary.

    Every word that is found is translated; every word that is not is
    NAMED (never silently dropped, never guessed)."""
    if not text.strip():
        return {"ok": False,
                "error": "چه چیزی را ترجمه کنم؟ مثال: «سلام را به انگلیسی ترجمه کن»"}
    data = _load()
    table = data.get("fa2en" if to_english else "en2fa", {})
    words = _normalize_fa(text).split()
    out: list[str] = []
    missing: list[str] = []
    for w in words:
        key = w.strip(".,!?؟،؛:«»\"'")
        hit = table.get(key) or table.get(key.lower())
        if hit:
            out.append(hit)
        else:
            # a two-word phrase join (pocket dictionaries hold phrases too)
            missing.append(key)
    if not out and missing:
        return {"ok": False, "error": (
            f"واژههای «{'، '.join(missing[:6])}» در واژهنامهٔ جیبیِ آفلاین من "
            "نیستند و ترجمهٔ حدسی نمیسازم. برای ترجمهٔ کامل: مدلِ زبانی را با "
            "UM_LLM_BASE_URL وصل کن."),
            "missing": missing}
    return {"ok": True, "translation": " ".join(out),
            "missing": missing or []}


class TranslateToolConnector:
    """The pocket dictionary through the Connector protocol (R79 B3)."""

    def __init__(self) -> None:
        from universal_mind.pantheon.contracts import Connector

        self._Connector = Connector

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:
        from universal_mind.pantheon.contracts import ConnectorResult

        text = str(params.get("text", "") or params.get("q", "") or "")
        to_en = params.get("to_english", True)
        out = translate(text, to_english=bool(to_en))
        if out.get("ok") is not True:
            return ConnectorResult(ok=False, output=None,
                                   error=str(out.get("error", "failed")))
        return ConnectorResult(ok=True, output=out)


__all__ = ["translate", "TranslateToolConnector"]
