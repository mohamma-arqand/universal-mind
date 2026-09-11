"""Multilingual understanding — a language-independent intent layer.

The mind should not care which human language a goal arrives in: "summarize the
report" and its Persian/French equivalent must land in the same execution loop.
This module is the normalization layer: it maps a raw utterance in any supported
language to a *language-independent intent signature* (action verb + subject
tokens), so downstream decomposition/arbitration sees one canonical form.

The reference mapper is a deterministic keyword dictionary (no I/O, no external
translator); it is deliberately small and auditable, and a full translator can be
injected later without changing the contract.

Deterministic and local.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedIntent:
    """A language-independent intent signature."""

    action: str                 # canonical action verb (English)
    subjects: tuple[str, ...]   # canonical subject tokens
    source_language: str        # detected source language ('en' | 'fa' | ...)


# A small, deterministic cross-language mapping: source token -> (action, subject).
_ACTION_MAP: dict[str, str] = {
    # English
    "summarize": "summarize", "write": "write", "translate": "translate",
    "analyze": "analyze", "compute": "compute", "compare": "compare",
    # Persian (فارسی)
    "خلاصه": "summarize", "خلاصه‌کن": "summarize", "جمع‌بندی": "summarize",
    "بنویس": "write", "بنويس": "write", "نوشتن": "write",
    "ترجمه": "translate", "ترجمه‌کن": "translate",
    "تحلیل": "analyze", "تحلیل‌کن": "analyze",
    "محاسبه": "compute", "حساب": "compute",
    "مقایسه": "compare",
}

_FA_MARKERS: tuple[str, ...] = (
    "خلاصه", "بنویس", "بنويس", "نوشتن", "ترجمه", "تحلیل", "محاسبه",
    "حساب", "مقایسه", "کردن", "کن", "چیست", "بده",
)


def _detect_language(text: str) -> str:
    """A coarse language detection: any Persian-action marker -> 'fa' else 'en'."""
    lowered = text.lower()
    return "fa" if any(m in lowered for m in _FA_MARKERS) else "en"


def _canonical_action(text: str) -> str:
    """Return the first canonical action found in the text (English or Persian)."""
    lowered = text.lower()
    for token, action in _ACTION_MAP.items():
        if token.lower() in lowered:
            return action
    # Fall back to the first substantive word as a weak action.
    import re

    words = re.findall(r"[a-z0-9]+", lowered)
    return words[0] if words else ""


def _subjects(text: str, action: str) -> tuple[str, ...]:
    """Extract canonical subject tokens (drop the action word and stop words)."""
    import re

    stop = {"the", "a", "an", "and", "of", "to", "for", "in", "with", "on"}
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9]+", lowered)
    # A Persian token (non-ascii) is kept as-is; English is lowercased already.
    subjects = []
    for t in tokens:
        if t in stop or t == action:
            continue
        if len(t) >= 2:
            subjects.append(t)
    return tuple(subjects[:5])


def normalize_intent(text: str) -> NormalizedIntent:
    """Normalize a cross-language utterance to a language-independent signature."""
    action = _canonical_action(text)
    return NormalizedIntent(
        action=action,
        subjects=_subjects(text, action),
        source_language=_detect_language(text),
    )