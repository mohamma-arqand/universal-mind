"""THE TEXT-SUMMARY TOOL — extractive Persian summarization, no LLM (R62 T3).

«خلاصه کن این متن را: …» was dead: the sentence is one of the most human
requests there is, and it needs NO network — a real extractive summary is
computable locally. This tool is honest by construction:

  - The summary is a SELECTION of the text's OWN sentences (never a
    generated sentence that was not there).
  - Scoring is word-overlap (TF over non-stopword tokens): the sentences
    that share the text's central vocabulary, plus the first sentence
    (which states the topic), rise to the top.
  - The output names what it did: how many sentences from how many,
    never a fake "این خلاصه است".
  - No text -> a NAMED refusal asking for the text.
"""

from __future__ import annotations

import re

from universal_mind.connectors import ConnectorResult

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Persian stopwords: the glue that carries no subject matter.
_STOP = {
    "و", "در", "به", "از", "که", "این", "آن", "با", "برای", "را", "است", "هست",
    "بود", "شد", "شده", "می", "های", "ها", "یک", "تا", "بر", "هم", "او", "ما",
    "شما", "آنها", "خود", "کن", "کند", "کنم", "نیز", "چون", "اما", "یا", "هر",
    "چه", "چی", "اینکه", "اگر", "پس", "همچنین", "مثلا", "یعنی", "روی", "درباره",
}

_SENT_SPLIT = re.compile(r"[.!?؟…]+[\n ]*")


def _tokens(sentence: str) -> list[str]:
    words = re.findall(r"[\u0600-\u06FF\u200c]+", sentence)
    return [w for w in words if len(w) > 1 and w not in _STOP]


def summarize(text: str, max_sentences: int = 3) -> dict[str, object]:
    """Extract the text's own most central sentences, honestly."""
    clean = (text or "").strip()
    if not clean:
        return {"ok": False, "error": "متنی برای خلاصه‌کردن پیدا نکردم — "
                                      "مثلا بگو: «خلاصه کن این متن را: …»",
                "kind": "no_text"}
    sentences = [s.strip() for s in _SENT_SPLIT.split(clean) if s.strip()]
    if max_sentences >= len(sentences):
        # the whole text fits the budget: the honest summary is all of it
        return {"ok": True, "summary": sentences, "sentences": len(sentences),
                "picked": len(sentences), "kind": "whole"}
    # TF over the text's own non-stopword tokens
    freq: dict[str, int] = {}
    for s in sentences:
        for t in _tokens(s):
            freq[t] = freq.get(t, 0) + 1
    # score: centrality (overlap with the whole) + a first-sentence bonus
    # (the opening sentence states the topic in almost every Persian text)
    scores: list[float] = []
    for i, s in enumerate(sentences):
        toks = _tokens(s)
        base = sum(freq.get(t, 0) for t in toks)
        norm = base / (len(toks) or 1)
        first_bonus = 1.5 if i == 0 else 0.0
        scores.append(norm + first_bonus)
    ranked = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)
    picked = sorted(ranked[:max_sentences])  # keep the original order
    return {"ok": True, "summary": [sentences[i] for i in picked],
            "sentences": len(sentences), "picked": len(picked), "kind": "extract"}


class TextSummaryConnector:
    """Adapts :func:`summarize` to the ``Connector`` protocol."""

    def connect(self, spec: object, params: dict[str, object]) -> ConnectorResult:
        text = str(params.get("text", "") or "")
        out = summarize(text, int(params.get("max_sentences", 3) or 3))
        if not out.get("ok"):
            return ConnectorResult(ok=False, output=None, error=str(out["error"]))
        return ConnectorResult(ok=True, output={
            k: v for k, v in out.items() if k not in ("ok", "error")
        })


__all__ = ["TextSummaryConnector", "summarize"]
