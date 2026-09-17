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
from pathlib import Path
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
        # Chart KIND words name the operation explicitly (میلهای/دایرهای/خطی/...);
        # the default remains the line chart.
        kind = "line"
        if "میلهای" in command or "ستونی" in command or "میله" in command:
            kind = "bar"
        elif "دایرهای" in command or "دایره" in command or "پایهای" in command:
            kind = "pie"
        elif "پراکنده" in command or "اسکتر" in command:
            kind = "scatter"
        elif "هیستوگرام" in command or "هیستوگرامش" in command:
            kind = "histogram"
        params: dict[str, Any] = {"operation": kind}
        if kind == "bar":
            params["categories"] = ["الف", "ب", "ج"][:len(data)] if data else None
            params["values"] = data
        elif kind == "pie":
            params["values"] = data
            params["labels"] = ["الف", "ب", "ج"][:len(data)] if data else None
        elif data:
            params["series"] = {"داده": data}
        if text:
            params["title"] = with_resolved_date(text, command)
        return params
    if capability == "pdf":
        # Operation words: the sentence can name a SPECIFIC document kind.
        _PDF_OP_WORDS: tuple[tuple[str, str], ...] = (
            ("فاکتور", "invoice"), ("قبض", "invoice"),
            ("نامه", "letterhead"), ("سربرگ", "letterhead"),
            ("جدول", "styled_table"), ("لیست", "bullet_list"),
            ("جلد", "cover_page"), ("کاور", "cover_page"),
        )
        for word, op in _PDF_OP_WORDS:
            if word in command:
                params = {"operation": op}
                if text:
                    params["title"] = with_resolved_date(text, command)
                return params
        # A Persian command deserves a Persian RTL document (not a Latin-only one):
        # the title and paragraphs are real Persian text, rendered RTL.
        # When the flow has a real image to embed (chart → pdf), the orchestration
        # layer upgrades persian_rtl → persian_report (image inside the report).
        params = {"operation": "persian_rtl"}
        title = with_resolved_date(text or "گزارش ذهن یکپارچه", command)
        params["title"] = title
        params["paragraphs"] = [
            "گزارش تولیدشده توسط حلقهی سنتز ذهن یکپارچه.",
            f"فرمان دریافتشده: {command}",
        ]
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
    if capability == "webfetch":
        # URL extraction: http(s)://... in the sentence, or a bare domain
        # after «آدرس». Honest: without a recognizable URL the fetch refuses.
        import re as _re

        m = _re.search(r"https?://\S+", command)
        if m:
            return {"operation": "fetch", "url": m.group(0)}
        m2 = _re.search(r"آدرس ([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", command)
        if m2:
            return {"operation": "fetch", "url": "https://" + m2.group(1)}
        return {}  # no URL found — the connector will refuse honestly

    if capability == "pdfreader":
        if path:
            return {"operation": "read_text", "path": path}
        return {"operation": "read_text"}  # OPEN: the flow picks the chain's pdf

    if capability == "excel":
        # «در اکسل بریز» — the flow fills headers/rows from the chain's real
        # numbers; an explicit path means reading an existing workbook back.
        if path:
            return {"operation": "read_table", "path": path}
        return {"operation": "write_table"}  # OPEN: the flow fills the table

    if capability == "ocr":
        # «متن تصویر را بخوان» — with a path in the sentence it is explicit;
        # without one the flow layer aims it at the chain's own image.
        if path:
            return {"operation": "read", "path": path}
        return {"operation": "read"}  # OPEN: the flow picks the chain's image

    if capability == "speech":
        # «بلند بخوان» says: read ALOUD what was made. With no explicit text in
        # the sentence, the flow layer fills the body with the chain's summary.
        if text and len(text) > 2:
            return {"operation": "speak", "text": text}
        return {"operation": "speak"}  # OPEN: the flow speaks the chain's summary

    if capability == "clipboard":
        # «بگذار/کپی کن» = write (the flow layer fills the text with what was
        # made); «بخوان/کپی چی توشه» = read. Default stays read (honest no-op
        # unless the sentence says otherwise).
        if "بخوان" in command or "چه چیزی" in command or "چیه" in command:
            return {"operation": "read"}
        if "بگذار" in command or "کپی" in command or "قرار بده" in command:
            return {"operation": "write"}  # text comes from the flow
        return {"operation": "read"}

    if capability == "notify":
        # The body defaults to the command itself, but the dataflow layer will
        # REPLACE a bare command echo with a real summary of what was made
        # (the toast should say what the chain produced, not echo the order).
        return {"operation": "notify", "title": text or "Universal Mind", "body": command}
    if capability == "vision":
        # «تحلیل تصویر» -> real OpenCV work on the operator's real file/folder.
        # With NO explicit target in the sentence, the operation stays OPEN so
        # the flow layer can choose the honest default: analyze the image the
        # chain itself just made (make → look → understand). With a target
        # named, the operator's intent stands.
        vision_params: dict[str, Any] = {}
        folder = resolve_folder(command)
        # Named analyses in the sentence are explicit intent (they win over the
        # flow's default stats): «تشخیص لبه» → edges, «کنتور» → contours.
        if "ساختار" in command:
            vision_params["operation"] = "chart_structure"
        elif "لبه" in command or "تشخیص لبه" in command:
            vision_params["operation"] = "edges"
        elif "کنتور" in command or "کانتور" in command:
            vision_params["operation"] = "contours"
        if path:
            vision_params["path"] = path
        elif folder:
            # Analyze the first real image in the resolved folder (if any).
            import os

            for entry in sorted(os.listdir(folder)):
                if entry.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    vision_params = {"operation": "contours", "path": str(Path(folder) / entry)}
                    break
        return vision_params  # empty = OPEN: the flow layer picks the chain's own image
    if capability == "ai":
        # «خوشهبندی»/«یادگیری» -> real ML over the numbers in the command.
        if "خوشه" in command and numbers:
            pairs = [[float(numbers[i]), float(numbers[i + 1])] for i in range(0, len(numbers) - 1, 2)]
            return {"operation": "cluster", "data": pairs}
        if numbers and len(numbers) > 1:
            xs = [[float(numbers[i])] for i in range(len(numbers) - 1)]
            ys = [float(numbers[i + 1]) for i in range(len(numbers) - 1)]
            return {"operation": "regression", "xs": xs, "ys": ys}
        return {"operation": "regression"}
    if capability == "database":
        # «چی ذخیره کردی؟» — a READ-back of the real persistent store: the
        # memory loop closes (store → recall → narrate).
        asking = any(w in command for w in ("چی ذخیره", "چه ذخیره", "نشونم بده", "نشان بده", "بخوان"))
        if asking:
            return {
                "operation": "query",
                "sql": "SELECT metric, value FROM chain_results "
                       "ORDER BY rowid DESC LIMIT 20",
                "persistent": True,
            }
        # «گزارش از ذخیرهشدهها» — the MEMORY becomes a DOCUMENT: the pdf
        # renders the stored chain_results as a real table (the read-back flow).
        if "گزارش از" in command and "ذخیره" in command:
            return {
                "operation": "query",
                "sql": "SELECT metric, value FROM chain_results "
                       "ORDER BY rowid DESC LIMIT 12",
                "persistent": True,
            }
        # «ذخیره کن» + extracted numbers -> a REAL insert (not an empty query):
        # the operator said store, so the numbers go into a real table — and the
        # PERSISTENT database (~/.universal-mind/mind.db), because data the
        # operator chose to store must survive the session, not die with it.
        # BUT when a computing capability is also routed (data/ai), the rows
        # must come from the COMPUTED results (the flow layer), not the raw
        # numbers — storing what was computed beats re-stating the input.
        if "ذخیره" in command and data:
            return {
                "operation": "insert_many",
                "table": "extracted_data",
                "rows": [{"value": str(n)} for n in data],
                "persistent": True,
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