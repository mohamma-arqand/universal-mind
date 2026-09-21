"""Spelling recovery — a typo is one step from recovery, never a dead end.

The router's vocabulary is a real Persian word list; when a command matches
NOTHING, the honest failure carries the nearest known words (bounded edit
distance), so «نقشه بکش» (not a vocabulary word) still points at «نمودار».
"""

from __future__ import annotations

import re

# The router's REAL vocabulary (word -> capability), mirrored from
# persian_router._VOCAB at import time — suggestions always point at a
# capability, never at a filler verb («کن» alone routes nowhere useful).
_VOCABULARY: tuple[str, ...] = ()

_FILLERS = frozenset({"کن", "کنید", "را", "و", "در", "به", "با", "از", "این", "آن", "همه"})

# R39: English near-misses — the operator mixes languages; a hint in their
# own tongue beats a bare refusal.
_ENGLISH_HINTS: tuple[tuple[str, str], ...] = (
    ("chart", "نمودار"), ("draw", "نمودار"), ("plot", "نمودار"),
    ("graph", "نمودار"), ("average", "میانگین"), ("mean", "میانگین"),
    ("read", "بخوان"), ("save", "ذخیره"), ("image", "عکس"),
    ("pdf", "سند"), ("speak", "صدا"), ("data", "داده"), ("report", "گزارش"),
)


def _load_vocabulary() -> tuple[str, ...]:
    """Mirror the live router vocabulary (capability words, fillers out)."""
    try:
        from universal_mind.persian_router import _VOCAB

        words = {w for w, _cap in _VOCAB if w not in _FILLERS and len(w) >= 3}
        return tuple(sorted(words))
    except Exception:  # noqa: BLE001 — suggestions degrade to empty, honest
        return ()


_VOCABULARY = _load_vocabulary()

_TOKEN_RE = re.compile(r"[\u0600-\u06FF\u200c]+")


def _edit_distance(a: str, b: str, cap: int = 3) -> int:
    """Bounded Levenshtein: returns > cap quickly when beyond reach."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        best = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur.append(v)
            best = min(best, v)
        if best > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def suggest_for(command: str, limit: int = 3) -> list[str]:
    """The nearest known words to this command's tokens (best-first)."""
    lowered = command.lower()
    english: list[str] = []
    for en, fa in _ENGLISH_HINTS:
        if en in lowered and fa not in english:
            english.append(fa)
    tokens = _TOKEN_RE.findall(command)
    if not tokens:
        return english[:limit]
    if english:
        return english[:limit]
    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 2:
            continue
        for word in _VOCABULARY:
            if word in seen:
                continue
            d = _edit_distance(token, word)
            if d <= 2:
                seen.add(word)
                scored.append((d, word))
    scored.sort()
    return [w for _, w in scored[:limit]]


__all__ = ["suggest_for"]