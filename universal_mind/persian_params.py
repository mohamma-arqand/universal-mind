"""Persian parameter extraction — pull real values out of the command itself.

«میانگین ۲ و ۴ و ۶ را حساب کن» must compute the mean of [2, 4, 6] — the numbers
in the sentence ARE the parameters. This module extracts them:

- numbers  : Persian digits (۰-۹), Arabic digits (٠-٩), and Western digits,
             including decimals, into a real float list;
- text     : quoted / «گیومه» strings, and text after «به نام» / «با متن»;
- paths    : Windows/Unix paths appearing in the command.

Deterministic and pure: a given sentence always yields the same parameters.
"""

from __future__ import annotations

import re
from typing import Any

from universal_mind.persian_date import with_resolved_date

_DIGIT_MAP = {
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}


def _normalize_digits(text: str) -> str:
    """Persian/Arabic digits → Western digits (so float parsing works)."""
    for fa, en in _DIGIT_MAP.items():
        text = text.replace(fa, en)
    return text


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_numbers(command: str) -> list[float]:
    """Every number in the command (Persian, Arabic, or Western digits) as floats."""
    normalized = _normalize_digits(command)
    return [float(m) for m in _NUMBER_RE.findall(normalized)]


def extract_numbers_between(command: str) -> list[float]:
    """Numbers joined by «و» (and) — the explicit list form: «۲ و ۴ و ۶»."""
    normalized = _normalize_digits(command)
    # A number followed by و followed by another number chains the list.
    chained = re.findall(
        r"-?\d+(?:\.\d+)?(?:\s+و\s+-?\d+(?:\.\d+)?)+", normalized
    )
    if not chained:
        return []
    numbers: list[float] = []
    for group in chained:
        numbers.extend(float(m) for m in _NUMBER_RE.findall(group))
    return numbers


def extract_text(command: str) -> str | None:
    """Quoted text («...» / "..." / '...') or the text after «با متن» / «به نام»."""
    for pattern in (
        r"«([^»]+)»",           # Persian guillemets
        r'"([^"]+)"',           # double quotes
        r"'([^']+)'",           # single quotes
        r"(?:با متن|به نام|با عنوان)\s+(.+?)(?:\s+و\s+|$)",
    ):
        m = re.search(pattern, command)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def extract_path(command: str) -> str | None:
    r"""A real file path appearing in the command (C:\..., D:/..., or /unix)."""
    normalized = _normalize_digits(command)
    m = re.search(r"[A-Za-z]:[\\/][^\s«»\"']+", normalized)
    if m:
        return m.group(0)
    m = re.search(r"(?<!\w)/[a-zA-Z0-9_\-./]+", normalized)
    return m.group(0) if m else None


_KNOWN_FOLDERS: dict[str, str] = {
    "دسکتاپ": "Desktop",
    "میز کار": "Desktop",
    "دانلود": "Downloads",
    "دانلودها": "Downloads",
    "اسناد": "Documents",
    "مستندات": "Documents",
    "عکس ها": "Pictures",
    "عکسها": "Pictures",
}


def resolve_folder(command: str) -> str | None:
    """A Persian folder name («از دسکتاپ») → the real Windows folder path.

    The path is resolved against the actual user profile, so «از دسکتاپ» really
    means C:\\Users\\<user>\\Desktop on this machine — not a placeholder.
    """
    import os
    from pathlib import Path

    profile = os.environ.get("USERPROFILE")
    if not profile:
        return None
    lowered = command.lower()
    for fa, folder in _KNOWN_FOLDERS.items():
        if fa in lowered:
            real = Path(profile) / folder
            if real.exists():
                return str(real)
    return None


def extract_params(command: str, capability: str) -> dict[str, Any]:
    """Build the real operation params for one capability from the command text.

    This is the bridge between what the operator SAID and what the suite needs:
    numbers become the data series, text becomes titles/content, paths become
    the source file. Each capability receives only the parameters it actually
    accepts (a capability's contract constrains what it is given).
    """
    numbers = extract_numbers(command)
    numbers_between = extract_numbers_between(command)
    text = extract_text(command)
    path = extract_path(command)
    data = numbers_between or numbers

    if capability == "data":
        if numbers:
            return {"operation": "stats", "data": data}
        return {"operation": "stats"}
    if capability == "chart":
        params: dict[str, Any] = {"operation": "line"}
        if data:
            params["series"] = {"داده": data}
        if text:
            params["title"] = with_resolved_date(text, command)
        return params
    if capability == "pdf":
        params = {"operation": "document"}
        if text:
            params["title"] = with_resolved_date(text, command)
        return params
    if capability == "image":
        if path:
            return {"operation": "info", "path": path}
        folder = resolve_folder(command)
        if folder:
            return {"operation": "info", "path": folder, "folder": folder}
        return {"operation": "info"}
    if capability == "media":
        return {"operation": "generate"}
    if capability == "archive":
        if text:
            return {"operation": "compress", "content": text}
        return {"operation": "compress", "content": command}
    if capability == "compute":
        if numbers and len(numbers) > 1:
            # «جمع ۲ و ۳» → a real JS expression over the extracted numbers.
            return {"operation": "evaluate", "expression": " + ".join(str(n) for n in numbers)}
        return {"operation": "evaluate"}
    if capability == "notify":
        return {"operation": "notify", "title": text or "Universal Mind", "body": command}
    if capability == "database":
        # «ذخیره کن» + extracted numbers -> a REAL insert (not an empty query):
        # the operator said store, so the numbers go into a real table.
        if "ذخیره" in command and data:
            return {
                "operation": "insert_many",
                "table": "extracted_data",
                "rows": [{"value": str(n)} for n in data],
            }
        return {"operation": "query"}
    return {}


__all__ = [
    "extract_numbers",
    "extract_numbers_between",
    "extract_params",
    "extract_path",
    "extract_text",
    "resolve_folder",
    "with_resolved_date",
]