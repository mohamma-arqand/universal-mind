"""R47 items 10-11 — the breathing vocabulary: words become capabilities.

Item 10: the harvest SUGGESTS — for each frequent unknown word, the nearest
capability name by edit distance is proposed («شاید منظورت نمودار بود؟»).
The operator can then confirm with «واژهی X یعنی Y» (the R46 overlay) and
the word stops being unknown forever.

Item 11: «چقدر یاد گرفتی؟» answers with the LEARNING RATIO — the share of
harvested unknowns that are resolved (defined by the operator, suggested
with a near match, or close enough to a real capability name). One honest
number that GROWS as the vocabulary breathes.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

# short junk / latin test tokens are not vocabulary worth learning
_JUNK = ("zzzq", "xyzq", "xyz", "abc", "test")


def _levenshtein(a: str, b: str) -> int:
    """Plain edit distance — no dependency, no guessing."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _persian_capability_words() -> dict[str, str]:
    """Persian word → capability, from the router's own live vocabulary."""
    try:
        from universal_mind.persian_router import _VOCAB

        return {str(word): str(cap) for word, cap in _VOCAB}
    except Exception:  # noqa: BLE001
        return {}


def _nearest_capability(term: str) -> tuple[str, int] | None:
    """The closest real Persian trigger word, by honest edit distance."""
    words = _persian_capability_words()
    if not words:
        return None
    best_word = min(words, key=lambda w: _levenshtein(term, w))
    dist = _levenshtein(term, best_word)
    return words[best_word], dist


def suggestions(*, db: DatabaseSuite | None = None,
                min_hits: int = 1, limit: int = 5) -> list[dict[str, Any]]:
    """Frequent unknowns with their nearest real capability (edit distance)."""
    store = db or DatabaseSuite.shared_persistent()
    try:
        q = store.query(
            "SELECT term, hits FROM unknown_terms "
            "WHERE hits >= ? ORDER BY hits DESC LIMIT 30",
            (int(min_hits),),
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001
        return []

    from universal_mind.learned_vocab import overlay

    known = {w for w in overlay(db=store)}
    out: list[dict[str, Any]] = []
    for r in rows:
        term = str(r["term"]).strip()
        if term in known or term.lower() in _JUNK or len(term) < 3:
            continue
        nearest = _nearest_capability(term)
        if nearest is None:
            break
        capability, dist = nearest
        if dist > max(2, len(term) // 4):
            continue  # nothing close enough — never a wild guess
        out.append({"term": term, "hits": int(r["hits"]),
                    "capability": capability, "distance": dist})
        if len(out) >= limit:
            break
    return out


def learning_ratio(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """The honest share of harvested unknowns that are no longer unknown."""
    store = db or DatabaseSuite.shared_persistent()
    try:
        q = store.query(
            "SELECT term, hits FROM unknown_terms ORDER BY hits DESC")
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001
        return {"ok": False, "total": 0, "resolved": 0, "ratio": 0.0}

    from universal_mind.learned_vocab import overlay

    known = {w for w in overlay(db=store)}
    words = _persian_capability_words()
    total = 0
    resolved = 0
    for r in rows:
        term = str(r["term"]).strip()
        if term.lower() in _JUNK or len(term) < 3:
            continue  # test junk never counts either way
        total += 1
        if term in known:
            resolved += 1  # the operator defined it
            continue
        if words and min(_levenshtein(term, w) for w in words) <= 2:
            resolved += 1  # close enough to a real trigger word (suggested)
    ratio = round(resolved / total, 4) if total else 0.0
    return {"ok": True, "total": total, "resolved": resolved,
            "ratio": ratio}


def learning_fa(info: dict[str, Any]) -> str:
    """One Persian line with the real ratio."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    pct = str(round(float(info["ratio"]) * 100)).translate(fa)
    total = str(int(info["total"])).translate(fa)
    resolved = str(int(info["resolved"])).translate(fa)
    return (f"درصدِ یادگیریِ واژگان: {pct}٪ — از {total} واژهی ناشناختهی "
            f"واقعی، {resolved} تا حل شده (تعریفشده یا نزدیک به قابلیتی واقعی)")


__all__ = ["learning_fa", "learning_ratio", "suggestions"]
