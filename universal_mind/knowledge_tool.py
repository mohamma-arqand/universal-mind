"""R79 B5 — KNOWLEDGE: a real offline factbook, honestly bounded.

The audit's refusal for «پایتخت فرانسه چیست؟» was honest but empty —
and «ایران چند استان دارد؟» died in «نشناختم». Knowledge is now the
34th real capability: a shipped Persian factbook (data/facts_fa.json)
of the core everyday facts — geography, history, science, culture —
looked up by a tolerant matcher. A hit answers with the fact AND its
source line; a miss is the honest refusal that names the boundary and
the road (UM_LLM_BASE_URL). NEVER a guess dressed as knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FACTBOOK = Path(__file__).resolve().parent / "data" / "facts_fa.json"


def _load() -> list[dict[str, str]]:
    try:
        return json.loads(_FACTBOOK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


_STOP = {"چیست", "چیست؟", "کیست", "کیست؟", "چیه", "چیه؟", "چند", "است",
         "هست", "بگو", "را", "در", "به", "از", "با", "برای", "و", "؟",
         "تعریف", "یعنی", "یکم", "درباره", "مروری", "کن"}


def _norm(s: str) -> str:
    return (s.replace("ی", "ی").replace("ك", "ک")
             .replace("\u200c", " ").replace("؟", " ").strip())


def _tokens(q: str) -> list[str]:
    words = [w.strip(".,؛:!«»\"'") for w in _norm(q).split()]
    return [w for w in words if w and w not in _STOP and len(w) > 1]


def lookup(question: str) -> dict[str, Any]:
    """Answer a knowledge question from the shipped factbook — or refuse."""
    toks = _tokens(question)
    if not toks:
        return {"ok": False, "error": "پرسشت را نفهمیدم — مثال: «پایتخت فرانسه چیست؟»"}
    best: tuple[int, dict[str, str]] | None = None
    for fact in _load():
        keys = fact.get("keys", [])
        score = 0
        for k in keys:
            k_norm = _norm(k)
            # a key fully inside the question scores highest
            if k_norm in _norm(question):
                score += 10 + len(k.split())
            else:
                # every matching token still counts
                kt = {t for t in k_norm.split() if len(t) > 1}
                score += sum(3 for t in toks if t in kt)
        # the answer body's own words must not carry the score alone
        if score > 0 and (best is None or score > best[0]):
            best = (score, fact)
    if best and best[0] >= 10:
        fact = best[1]
        return {"ok": True, "fact": fact["fact"],
                "source": fact.get("source", "کتابِ حقایقِ داخلی")}
    return {"ok": False, "error": (
        "این را در کتابِ حقایقِ آفلایمم ندارم و حدس نمیزنم. یا مدلِ زبانی را "
        "با UM_LLM_BASE_URL وصل کن، یا پرسش را دقیقتر بپرس.")}


def register() -> type | None:  # pragma: no cover - registry hook
    class KnowledgeToolConnector:
        def connect(self, spec: Any, params: dict[str, Any]) -> Any:
            from universal_mind.pantheon.contracts import ConnectorResult

            out = lookup(str(params.get("question", params.get("q", ""))))
            if out.get("ok") is not True:
                return ConnectorResult(ok=False, output=None,
                                       error=str(out.get("error", "")))
            return ConnectorResult(ok=True, output=out)

    return KnowledgeToolConnector


__all__ = ["lookup"]
