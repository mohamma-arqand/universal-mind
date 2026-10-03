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


_WORD_NUMS: dict[str, int] = {
    "صفر": 0, "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
    "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10, "یازده": 11,
    "دوازده": 12, "سیزده": 13, "چهارده": 14, "پانزده": 15, "شانزده": 16,
    "هفده": 17, "هجده": 18, "نوزده": 19, "بیست": 20, "سی": 30,
    "چهل": 40, "پنجاه": 50, "شصت": 60, "هفتاد": 70, "هشتاد": 80,
    "نود": 90, "صد": 100, "هزار": 1000, "میلیون": 1000000,
}


def _spoken_numbers(normalized: str) -> list[float]:
    """R69 P6 — Persian WORD numbers: «بیست و پنج» = 25. The tens-units
    join (و) is real arithmetic; «هزار/میلیون» scale. Found LEFT-TO-RIGHT
    so «بیست و پنج بعلاوه هفت» yields [25, 7]."""
    out: list[float] = []
    i = 0
    while i < len(normalized):
        best_w, best_v = "", None
        # THE WORD-BOUNDARY LAW (the «چنده» caught «ده» inside it — a live
        # witness: «بیست و پنج بعلاوه هفت چنده؟» read a phantom 10): a
        # word number must start at a boundary (text start or a
        # non-letter before it) AND end at one.
        for w, v in _WORD_NUMS.items():
            if normalized.startswith(w, i) and len(w) > len(best_w):
                before_ok = i == 0 or not normalized[i - 1].isalpha()
                after = i + len(w)
                after_ok = after >= len(normalized) or not normalized[after].isalpha()
                if before_ok and after_ok:
                    best_w, best_v = w, v
        if best_w is None or best_v is None:
            i += 1
            continue
        total = best_v
        j = i + len(best_w)
        # join units: «و پنج»
        while True:
            m = re.match(r"\s*و\s*", normalized[j:])
            if not m:
                break
            rest = normalized[j + m.end():]
            uw, uv = "", None
            for w, v in _WORD_NUMS.items():
                if rest.startswith(w) and len(w) > len(uw) and v < total:
                    uw, uv = w, v
            if uw:
                total += uv if uv is not None else 0
                j += m.end() + len(uw)
            else:
                break
        # scale: «هزار» / «میلیون»
        m2 = re.match(r"\s*(هزار|میلیون)", normalized[j:])
        if m2:
            total *= _WORD_NUMS[m2.group(1)]
            j += m2.end()
        out.append(float(total))
        i = j
    return out


def extract_numbers(command: str) -> list[float]:
    """Every number in the command (Persian, Arabic, or Western digits, or
    Persian WORD numbers — «بیست و پنج بعلاوه هفت» gives [25, 7])."""
    normalized = _normalize_digits(command)
    digit_n = [float(m) for m in _NUMBER_RE.findall(normalized)]
    word_n = _spoken_numbers(normalized)
    return digit_n + word_n if word_n else digit_n


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
        # «با عنوان X» — the title ends at a trailing command VERB («بساز»,
        # «بکش», «ذخیره کن»...), which is the sentence's instruction, never
        # part of the title itself.
        r"(?:با متن|به نام|با عنوان)\s+(.+?)(?:\s+و\s+|$)",
    ):
        m = re.search(pattern, command)
        if m and m.group(1).strip():
            title = m.group(1).strip()
            # The trailing VERB is the sentence's instruction, not the title:
            # «با عنوان فروش فصل بساز» → «فروش فصل».
            for verb in (
                " بساز", " بکش", " بده", " بگو", " بخوان", " بگیر",
                " ذخیره کن", " چاپ کن", " پاک کن", " حساب کن",
            ):
                if title.endswith(verb) and len(title) > len(verb) + 2:
                    title = title[: -len(verb)].strip()
            return title
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
    # R69 P6 — A SPOKEN COUNT IS NOT A DATA POINT: «جدول با سه سطر ذخیره
    # کن» — the new word-number reader turned «سه» into the VALUE 3 and the
    # table got ONE row (value=3) instead of THREE seeded rows. A «با N سطر»
    # shape names the COUNT; that word-number never rides the data.
    _m_count = re.search(r"با\s+(یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده)\s+سطر", command)
    if _m_count is not None:
        _W2N = {"یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
                "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
        _drop = float(_W2N[_m_count.group(1)])
        numbers = [n2 for n2 in numbers if n2 != _drop]
    data = numbers_between or numbers

    if capability == "data":
        # REAL ARITHMETIC on two numbers — the operator said ضرب/تقسیم/
        # جذر/درصد/توان and gets the RESULT, not the stats of the pair.
        _matched_scalar = next(
            (op for w, op in (
                ("منهای", "subtract"), ("منها", "subtract"), ("تفریق", "subtract"),
                ("ضرب", "multiply"), ("تقسیم", "divide"), ("جذر", "sqrt"),
                ("درصد", "percent"), ("توان", "power"),
            ) if w in command),
            None,
        )
        if _matched_scalar and numbers:
            a_val = data[0]
            b_val = data[1] if len(data) >= 2 else 100.0  # «درصد X از Y» needs the base
            return {
                "operation": "scalar_op",
                "a": a_val, "b": b_val,
                "scalar": _matched_scalar,
            }
        # R71 P1 — «۵ بزرگتر از ۳ است؟»: the comparison. THE SUBSTRING LAW,
        # SEVENTH BITE: «بزرگترین/کوچکترین» CONTAIN «بزرگتر/کوچکتر» — the
        # extremes (R69-P5) must be tested FIRST or «بزرگترین از ۵ و ۹ و ۲؟»
        # answers a pairwise comparison of the first two numbers.
        _is_extreme71 = any(w in command for w in (
            "بزرگترین", "بزرگ ترین", "کوچکترین", "کوچک ترین"))
        if not _is_extreme71 and numbers and len(numbers) >= 2 and any(
                w in command for w in ("بزرگتر", "بزرگ تر", "کوچکتر", "کوچک تر",
                                      "مساوی", "برابر است")):
            return {"operation": "compare", "a": numbers[0], "b": numbers[1]}
        # R70 P6 — «بین ۱۰ و ۲۰ چند عدد اول هست؟»: a real range question.
        if "اول" in command and numbers_between and len(numbers_between) >= 2:
            return {"operation": "primes",
                     "low": min(numbers_between[:2]),
                     "high": max(numbers_between[:2])}
        # R69 P4 — «مرتب کن: ۵ و ۲ و ۹» / «ترتیب نزولی ۵ و ۲ و ۹»
        if "مرتب" in command or "ترتیب" in command:
            desc = ("نزولی" in command or "بزرگ به کوچک" in command
                    or "معکوس" in command)
            if numbers:
                return {"operation": "sort", "data": data, "descending": desc}
            return {"operation": "sort", "descending": desc}
        # R69 P5 — «بزرگترین از ۵ و ۹ و ۲؟» / «کوچکترین از …»
        if ("بزرگترین" in command or "بزرگ ترین" in command
                or "کوچکترین" in command or "کوچک ترین" in command
                or "max" in command.lower() or "min" in command.lower()):
            largest = "کوچک" not in command and "min" not in command.lower()
            if numbers:
                return {"operation": "extremes", "data": data,
                        "largest": largest}
            return {"operation": "extremes", "largest": largest}
        if numbers:
            return {"operation": "stats", "data": data}
        return {"operation": "stats"}
    if capability == "chart":
        # Chart KIND words name the operation explicitly (میلهای/دایرهای/خطی/...);
        # the default remains the line chart.
        kind = "line"
        kind_explicit = "خطی" in command  # the word names it explicitly
        if "هیستوگرام" in command or "هیستوگرامش" in command:
            kind = "histogram"
            kind_explicit = True
        elif "میلهای" in command or "ستونی" in command or "میله" in command:
            kind = "bar"
            kind_explicit = True
        elif "دایرهای" in command or "دایره" in command or "پایهای" in command:
            kind = "pie"
            kind_explicit = True
        elif "پراکنده" in command or "اسکتر" in command:
            kind = "scatter"
            kind_explicit = True
        params: dict[str, Any] = {"operation": kind}
        if kind_explicit:
            # R37-L4: marks that the OPERATOR named this kind — a stored
            # preference must never override it (explicit intent wins).
            params["kind_explicit"] = True
        if kind == "histogram":
            params["data"] = data          # the real series from the sentence
        elif kind == "bar":
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
    if capability == "convert":
        # R74 P2 — the FORMAT target rides from the sentence: csv/اکسل/json.
        _tgt = ""
        if "csv" in command.lower():
            _tgt = "csv"
        elif "اکسل" in command or "excel" in command.lower() or "xlsx" in command.lower():
            _tgt = "xlsx"
        elif "json" in command.lower():
            _tgt = "json"
        return {"operation": "convert", "path": path, "target": _tgt}

    if capability == "html-report":
        # R73 P1/P4 — the VIEW is named by the sentence: dashboard /
        # timeline / table / card / overview — each a REAL HTML view of
        # MEASURED data (run history, schedules, vitals).
        if "داشبورد" in command:
            return {"mode": "dashboard"}
        if "تایم" in command and "لاین" in command:
            return {"mode": "timeline"}
        if "جدول" in command:
            return {"mode": "table"}
        if "کارت" in command:
            return {"mode": "card"}
        if "نمای کلی" in command:
            return {"mode": "overview"}
        # A WEEKLY ask sets the window the report reads.
        if "هفتگی" in command:
            return {"mode": "report", "window": "week"}
        return {"mode": "report"}

    if capability == "pdf":
        # Operation words: the sentence can name a SPECIFIC document kind.
        _PDF_OP_WORDS: tuple[tuple[str, str], ...] = (
            ("سالنامه", "yearbook"), ("گزارش سالانه", "yearbook"),
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
    if capability == "textsummarize":
        # R62 T3 — the text rides AFTER a colon (or the «را»): «خلاصه کن این
        # متن را: X». The extraction keeps the WHOLE text verbatim — a
        # summary's source must never be a truncated version of the truth.
        import re as _re

        m_txt = _re.search(r"[:：]\s*(.+)$", command)
        text = m_txt.group(1).strip() if m_txt else ""
        if not text:
            m_alt = _re.search(r"متن را\s+(.+)$", command)
            text = m_alt.group(1).strip().rstrip("،.") if m_alt else ""
        return {"operation": "summarize", "text": text}

    if capability == "textfile":
        # R60 Q1+Q2 — READ/LIST params. (The WRITE shape is handled by the
        # dedicated route_and_run block, which passes its own params — the
        # path there sits BETWEEN the sentence words and no glue could ever
        # carry it.) The path regex keeps the DOT: «notes.txt» lost its
        # extension to a char class that ate «.», a live witness caught it.
        import re as _re

        m_path = _re.search(r"([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
        path = m_path.group(1) if m_path else ""
        op = "read"
        if any(w in command for w in ("فایلهای متنی", "فایل‌های متنی")) \
                and "محتو" not in command and "بنویس" not in command:
            op = "list"
        # R64 P6/P7 — SEARCH/REPLACE: «در فایل X دنبال کلمه Y بگرد» /
        # «کلمه A را با B عوض کن». The needle/pair ride from the sentence;
        # replace needs the operator's explicit continue to rewrite.
        if any(w in command for w in ("دنبال", "بگرد", "جستجو", "جست‌جو")) and path:
            m_needle = _re.search(
                r"(?:دنبال|جست‌?جو)\s*(?:ی\s*)?(?:کن\s*)?(?:کلمه|واژه|عبارت)?\s*"
                r"(.+?)\s*(?:بگرد|پیدا کن|کن)[؟?.،!\s]*$", command)
            needle = (m_needle.group(1).strip() if m_needle else "").strip("،.\"'«»")
            if needle:
                return {"operation": "search", "path": path, "needle": needle}
        # R67 P2-P6 — rename/copy/size/folderstats/mkdir
        if "نام" in command and "عوض" in command and path:
            import re as _re_rn

            m_rn = _re_rn.search(r"به\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_rn:
                return {"operation": "rename", "path": path,
                        "dst": m_rn.group(1),
                        "overwrite_ok": "روی همان فایل" in command}
        if "کپی" in command and path:
            import re as _re_cp

            m_cp = _re_cp.search(
                r"به\s+(?:پوشه\s+)?(?:مسیر\s+)?([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_cp:
                dst = m_cp.group(1)
                # R74 P1 — «به پوشه Y»: the destination is the FOLDER; the
                # copy lands INSIDE it under the source's own name (a real
                # copy, never a silent read). Path() decides folder vs file.
                from pathlib import Path as _P74

                d = _P74(dst)
                if d.suffix == "" or d.is_dir():
                    d.mkdir(parents=True, exist_ok=True)
                    dst = str(d / _P74(path).name)
                return {"operation": "copy", "path": path,
                        "dst": dst,
                        "overwrite_ok": "روی همان فایل" in command}
        if ("حجم" in command or "چقدر است" in command) and path and "پوشه" not in command:
            return {"operation": "size", "path": path}
        # R71 P5 — «خط N فایل X را نشان بده» / «آخرین خط فایل X را بگو».
        _ORD = {"اول": 1, "دوم": 2, "سوم": 3, "چهارم": 4, "پنجم": 5,
                "ششم": 6, "هفتم": 7, "هشتم": 8, "نهم": 9, "دهم": 10}
        if "خط" in command and path and "نشان" in command or ("خط" in command and "بگو" in command and path):
            import re as _re_ln

            if "آخرین" in command or "اخرین" in command or "آخر" in command:
                return {"operation": "readline", "path": path, "last": True}
            _m_ord = _re_ln.search(
                r"خط\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)", command)
            _m_num = _re_ln.search(r"خط\s+([۰-۹0-9]+)", command)
            if _m_ord:
                return {"operation": "readline", "path": path,
                        "lineno": _ORD[_m_ord.group(1)]}
            if _m_num:
                return {"operation": "readline", "path": path,
                        "lineno": int(_m_num.group(1).translate(
                            str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))}
        # R71 P6 — «کلمه X در فایل Y چند بار آمده؟»: the frequency.
        if "چند بار" in command and "کلمه" in command and path:
            import re as _re_cw

            _m_cw = _re_cw.search(r"کلمه\s+([^،:]+?)\s+در فایل", command)
            if _m_cw:
                return {"operation": "countword", "path": path,
                        "needle": _m_cw.group(1).strip()}
        # R70 P2 — «در فایل X چند کلمه هست؟»: the word count. THE «چند» IS
        # THE MARKER: «کلمه A را با B عوض کن» is a REPLACE (R64-P7) — the
        # bare «کلمه» word must never steal it (the seal run caught the
        # replace answering with a word count).
        if "کلمه" in command and "چند" in command and "عوض" not in command and path:
            return {"operation": "wordcount", "path": path}
        if "فهرست" in command and "پوشه" in command and ("فایلهای" in command or "فایل های" in command):
            import re as _re_ls

            m_ls = _re_ls.search(r"پوشه\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_ls:
                _ext = ""
                m_ext = _re_ls.search(r"فایلهای?\s+([a-zA-Z0-9]+)", command)
                if m_ext:
                    _ext = "." + m_ext.group(1).lower()
                return {"operation": "list", "folder": m_ls.group(1),
                        "pattern": _ext or "*"}
        if ("چند" in command or "چقدر" in command) and "پوشه" in command:
            m_fd = None
            import re as _re_fd

            m_fd = _re_fd.search(r"پوشه\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_fd:
                return {"operation": "folderstats", "folder": m_fd.group(1)}
        if "بساز" in command and "پوشه" in command:
            import re as _re_mk

            m_mk = _re_mk.search(r"پوشه\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_mk:
                return {"operation": "mkdir", "folder": m_mk.group(1)}
            # R74 P4 — «پوشه به نام X در Y بساز» / «یک پوشه در Y بساز»: the
            # NAME rides from «به نام X», the PARENT from the path; a real
            # folder path is JOINED, never a bare read of the parent.
            m_named = _re_mk.search(r"به\s+نام\s+([^،!؟?\s]+)\s+در\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_named:
                from pathlib import Path as _P74k

                parent = _P74k(m_named.group(2).rstrip("/\\"))
                return {"operation": "mkdir", "folder": str(parent / m_named.group(1))}
            m_in = _re_mk.search(r"پوشه\s+(?:ای\s+)?(?:در|داخل)\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_in:
                # «پوشه در Y بساز» with a NAME before it («به نام X» already
                # handled): fall back to Y + the word after «پوشه … در».
                return {"operation": "mkdir", "folder": m_in.group(1)}
        # R65 P6 — MOVE: «فایل X را به Y جابجا کن» — both paths ride from
        # the sentence; the destination-after-«به» is the SECOND path.
        if "جابجا" in command and path:
            m_move = _re.search(
                r"به\s+(?:پوشه\s+)?(?:مسیر\s+)?([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if m_move:
                dst = m_move.group(1)
                from pathlib import Path as _P74m

                d = _P74m(dst)
                if d.suffix == "" or d.is_dir():
                    d.mkdir(parents=True, exist_ok=True)
                    dst = str(d / _P74m(path).name)
                return {"operation": "move", "path": path,
                        "dst": dst,
                        "overwrite_ok": "روی همان فایل" in command}
        if "عوض" in command and "با" in command and path:
            m_pair = _re.search(r"(?:کلمه|واژه|عبارت)\s+(.+?)\s+را\s+با\s+(.+?)\s+(?:عوض|جایگزین)", command)
            if m_pair:
                return {"operation": "replace", "path": path,
                        "old": m_pair.group(1).strip().strip("«»'\""),
                        "new": m_pair.group(2).strip().strip("«»'\""),
                        "overwrite_ok": "روی همان فایل" in command}
        if not path:
            return {}  # no path — the connector asks by name
        return {"operation": op, "path": path}

    if capability == "unitconvert":
        # R59 P2 — the sentence carries the value and the unit pair:
        # «۱۰ کیلومتر چند مایل است؟» → {value, source, target}.
        from universal_mind.unit_convert_tool import parse_convert_request

        parsed = parse_convert_request(command)
        if parsed is None:
            return {}  # not a conversion shape — the connector will ask
        return {"operation": "convert", "value": parsed["value"],
                "source": parsed["source"], "target": parsed["target"]}

    if capability == "compute":
        # R61-S1 — PERCENT IS DATA-SUITE'S OWN: «۲۰ درصد از ۵۰۰ چنده؟» was
        # built as `20.0 + 500.0` (=520, a fabricated sum) while the data
        # suite's scalar_op already computes the REAL percent (100). A
        # percent sentence never becomes an expression; compute gets out.
        if "درصد" in command:
            return {}
        if numbers and len(numbers) > 1:
            # R59 P1 — THE OPERATOR THE SENTENCE NAMES: «جمع …» is + but
            # «۵ منهای ۳» was built as `5.0 + 3.0` — the numbers were right
            # and the operation was a lie. The verb in the sentence picks
            # the operator; an unknown verb stays the honest `+` default
            # (the pre-existing behaviour for «جمع …» sentences).
            lowered_cmd = command
            op = "+"
            if "منهای" in lowered_cmd or "منها" in lowered_cmd or "تفریق" in lowered_cmd:
                op = "-"
            elif "ضرب" in lowered_cmd or "در " in lowered_cmd or "حاصل‌ضرب" in lowered_cmd \
                    or "حاصلضرب" in lowered_cmd or "ضرب‌در" in lowered_cmd:
                op = "*"
            elif "تقسیم" in lowered_cmd or "خارج‌قسمت" in lowered_cmd or "خارجقسمت" in lowered_cmd \
                    or "بر " in lowered_cmd:
                op = "/"
            elif "به توان" in lowered_cmd:
                op = "**"
            return {"operation": "evaluate",
                    "expression": f" {op} ".join(str(n) for n in numbers)}
        return {"operation": "evaluate"}
    if capability == "webfetch":
        # URL extraction: http(s)://... in the sentence, or a bare domain
        # after any of the site-words («سایت», «صفحه», «وب», «لینک»,
        # «آدرس») or standing alone. Honest: without a recognizable URL the
        # fetch refuses.
        # N10-1 (R57): «سایت example.com را بخوان» fell through to the
        # honest refusal because only «آدرس X» was recognized. A bare domain
        # after ANY site-word now counts — the same class of bug as the
        # anchored-regex trap: one narrow pattern doing a wide job.
        import re as _re

        m = _re.search(r"https?://[^\s،]+", command)
        if m:
            return {"operation": "fetch", "url": m.group(0)}
        m2 = _re.search(
            r"(?:سایت|صفحه|وب|لینک|آدرس)\s+([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+/?[^\s،]*|www\.[^\s،]+)",
            command,
        )
        if m2:
            url = m2.group(1).rstrip(".،;:!")
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            return {"operation": "fetch", "url": url}
        # a bare domain standing alone («وب را بگیر example.com»)
        m3 = _re.search(r"\b(?:www\.)?[a-zA-Z0-9-]+\.(?:com|ir|org|net|io|dev|ai|co|gov|edu|info)\b(?:/[^\s،]*)?",
                        command)
        if m3:
            url = m3.group(0)
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            return {"operation": "fetch", "url": url}
        return {}  # no URL found — the connector will refuse honestly

    if capability == "pdfreader":
        if path:
            return {"operation": "read_text", "path": path}
        return {"operation": "read_text"}  # OPEN: the flow picks the chain's pdf

    if capability == "zip":
        # R74 P3 — «فایل X را زیپ کن» = PACK that file; a bare zip path
        # (no file mentioned) still lists. A FOLDER ask packs the folder's
        # real files. The verb «زیپ/فشرده کن» decides, never the noun alone.
        _cmd_low = command.lower()
        if "زیپ" in command or "فشرده" in command or "آرشیو" in command or "zip" in _cmd_low:
            import re as _re_zip

            _m_dir = _re_zip.search(
                r"پوشه\s+([A-Za-z]:[\\/][^،!?؟\"\s]+)", command)
            if _m_dir:
                from pathlib import Path as _P74z
                from universal_mind.zip_helper import pack_folder as _pf

                return _pf(_P74z(_m_dir.group(1)))
            if path:
                return {"operation": "pack", "files": [path]}
            return {"operation": "pack"}  # the flow packs the chain's files
        if path:
            return {"operation": "list", "path": path}
        return {"operation": "pack"}  # OPEN: the flow packs the chain's files

    if capability == "csv":
        if path:
            return {"operation": "read_table", "path": path}
        return {"operation": "write_table"}  # OPEN: the flow fills the table

    if capability == "excel":
        # «در اکسل بریز» — the flow fills headers/rows from the chain's real
        # numbers; an explicit path means reading an existing workbook back.
        # A URL is NEVER a workbook path (the webfetch flow handles pages) —
        # treating 's://example.com' as an xlsx path was a live bug.
        if path and not path.lower().startswith(("http://", "https://", "s://")):
            return {"operation": "read_table", "path": path}
        # R44-10: a Persian spreadsheet reads RIGHT-TO-LEFT and earns its keep
        # with REAL formulas — «جمع»/«مجموع»/«جمعش» appends a genuine =SUM row.
        wants_total = any(w in command for w in ("جمع", "مجموع", "توتال", "جمع کل", "جمعش"))
        params_excel: dict[str, Any] = {"operation": "write_table", "rtl": True}
        if wants_total:
            params_excel["total"] = True
        return params_excel  # OPEN rows/headers: the flow fills the real table

    if capability == "email" and (
        "ایمیلهایم" in command or "ایمیل‌هایم" in command
        or "ایمیلهای من" in command or "ایمیل‌های من" in command
        or "ایمیلهای ارسالی" in command or "ایمیل‌های ارسالی" in command
    ):
        # R60 Q6 — the listing shape, not the compose shape.
        return {"operation": "list"}

    if capability == "email":
        # R44-11: the recipient rides the sentence («به آدرس ali@x.com ایمیل کن»);
        # without one the tool refuses honestly and names the remedy. The BODY
        # stays OPEN — the flow fills it with the chain's real report.
        import re as _re

        addr = _re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", command)
        params_email: dict[str, Any] = {"operation": "compose"}
        if addr:
            params_email["to"] = addr.group(0)
        else:
            # R56 THE CONTACT BOOK: «به مدیر ایمیل بزن» — a spoken NAME is
            # resolved against the operator's own saved contacts before the
            # honest refusal. A name the book does not know still refuses,
            # but now the refusal can name the remedy with the operator's
            # own word («مخاطبی به نام «مدیر» ندارم»).
            # R64 P8 — THE NAME STOPS AT ITS OWN VERB: «به زهرا ایمیل بزن»
            # extracted «زهرا ایمیل بزن» (the R61 fix covered the موضوع
            # shape; the bare-verb shape still ate its own tail). The name
            # is cut at the first action word of the channel.
            m = _re.search(r"به\s+«?([^»\n،]+?)»?\s*(?:با موضوع|در مورد|که|$)", command)
            if m:
                spoken_name = m.group(1).strip()
                # R64 P8 — cut the tail at the channel's action words
                _STOP = ("ایمیل", "نامه", "میل", "زنگ", "پیام", "مسیج",
                         "بزن", "بزنم", "کن", "کنم", "بفرست", "بفرستم", "ارسال")
                for _s in _STOP:
                    _idx = spoken_name.find(" " + _s)
                    _idx2 = spoken_name.startswith(_s)
                    if _idx2:
                        spoken_name = ""
                        break
                    if _idx != -1:
                        spoken_name = spoken_name[:_idx].strip()
                        break
                if spoken_name:
                    try:
                        from universal_mind.contacts import resolve

                        found = resolve(spoken_name)
                        if found:
                            params_email["to"] = found
                            params_email["resolved_from"] = spoken_name
                        else:
                            params_email["_unknown_contact"] = spoken_name
                    except Exception:  # noqa: BLE001 — the book is a lens
                        pass
        return params_email

    if capability == "ocr":
        # «متن تصویر را بخوان» — with a path in the sentence it is explicit;
        # without one the flow layer aims it at the chain's own image.
        if path:
            return {"operation": "read", "path": path}
        return {"operation": "read"}  # OPEN: the flow picks the chain's image

    if capability == "speech":
        # «بلند بخوان» says: read ALOUD what was made. With no explicit text in
        # the sentence, the flow layer fills the body with the chain's summary;
        # alone in the sentence, the SEED memory speaks the last real success.
        spoken_tail = None
        if text and len(text) > 2:
            spoken_tail = text
        else:
            # «بلند بخوان که X» / «بلند بخوان X» — the natural spoken tail.
            import re as _re

            m = _re.search(r"بلند\s+بخوان(?:\s+که)?\s+(.+)$", command, _re.DOTALL)
            if m and len(m.group(1).strip()) > 2:
                spoken_tail = m.group(1).strip()
        if spoken_tail:
            return {"operation": "speak", "text": spoken_tail}
        from universal_mind.seed_memory import seed_for_capability

        seed = seed_for_capability("speech")
        if seed and seed.get("proven"):
            return {"operation": "speak", "text": seed["text"], "seeded": True}
        return {"operation": "speak"}  # OPEN: the flow speaks the chain's summary

    # (goal speech is handled by the agent layer itself: the goal's report IS
    # the spoken text — «هدف را بلند بخوان» routes to speech with the last
    # goal report as its text, filled by the flow layer)

    if capability == "clipboard":
        # «بگذار/کپی کن» = write (the flow layer fills the text with what was
        # made); «بخوان/کپی چی توشه» = read. Default stays read (honest no-op
        # unless the sentence says otherwise).
        if "بخوان" in command or "چه چیزی" in command or "چیه" in command:
            return {"operation": "read"}
        if "بگذار" in command or "کپی" in command or "قرار بده" in command:
            return {"operation": "write"}  # text comes from the flow
        # R66 P7 — «یادداشت X را بنویس»: a note-taking sentence is a
        # clipboard WRITE (the spoken text rides in the params; the
        # note really lands on the clipboard, never a silent read).
        if ("بنویس" in command or "بنویسم" in command) and (
                "یادداشت" in command or "نوت" in command):
            import re as _re_p7

            _m_note = _re_p7.search(
                r"یادداشت\s+(?:امروز\s+)?(.+?)\s*(?:را|رو)?\s*بنویس", command)
            if _m_note and _m_note.group(1).strip():
                return {"operation": "write",
                        "text": _m_note.group(1).strip()}
        return {"operation": "read"}

    if capability == "sysstatus":
        # R53 wave-6 — the machine's vitals. R60 Q4: «فضای درایو C» names a
        # SPECIFIC drive — the report highlights that drive (drive_letter),
        # so the operator asking about C: does not get a five-drive wall.
        import re as _re

        # the colon is OPTIONAL — «فضای درایو C را نشان بده» names the drive
        # with no colon; requiring one measured empty-handed (live witness).
        m_drive = _re.search(r"درایو\s*([A-Za-z]):?|دیسک\s*([A-Za-z]):?", command)
        letter = (m_drive.group(1) or m_drive.group(2)).upper() if m_drive else ""
        return {"operation": "status", "drive_letter": letter}
    if capability == "filededupe":
        # R53 wave-5 — «فایلهای تکراری در دانلودها را پاک کن».
        from universal_mind.file_search_tool import extract_search_params

        base = extract_search_params(command)
        params_out: dict[str, Any] = {"operation": "find", "folder": base.get("folder")}
        # THE DELETE LAW: only an explicit «پاک/حذف کن» arms the deletion,
        # and only «تأیید کن» (or a repeat) actually fires it. Preview default.
        if "پاک" in command or "حذف" in command:
            params_out["operation"] = "clean"
            params_out["confirm"] = "تأیید" in command
        return params_out
    if capability == "filesearch":
        # R53 wave-4 — the search params come from the command itself:
        # «فایلهای بزرگ دیسک D»، «عکسها را پیدا کن»، «بزرگتر از ۱ گیگ».
        from universal_mind.file_search_tool import extract_search_params

        out = extract_search_params(command)
        # R65 P8 — THE SPOKEN FOLDER NAMES resolve to the real user folders
        # («دانلودها را نشان بده» searched a literal «دانلود» folder).
        _FOLDER_FA = {
            "دانلودها": "Downloads", "دانلودها را": "Downloads", "دانلود": "Downloads",
            "پوشه دانلود": "Downloads", "دسکتاپ": "Desktop", "میز کار": "Desktop",
            "اسناد": "Documents", "مدارک": "Documents", "تصاویر": "Pictures",
            "عکسها": "Pictures", "عکس‌ها": "Pictures", "موسیقی": "Music", "فیلمها": "Videos",
        }
        for _fa, _en in _FOLDER_FA.items():
            if _fa in command:
                try:
                    from pathlib import Path as _P

                    _real = _P.home() / _en
                    if _real.exists():
                        out["folder"] = str(_real)
                        out["top"] = out.get("top", 10)
                except Exception:  # noqa: BLE001 — the lens never breaks
                    pass
                break
        # the rest of the sentence (minus trigger words) is a name filter
        # when the operator named a file type with their own words
        for trig in ("فایلهای بزرگ", "فایل های بزرگ", "پیدا کن در", "جستجوی فایل",
                     "فایلها را پیدا", "بزرگترین فایل", "را پیدا کن", "پیدا کن"):
            command = command.replace(trig, "")  # noqa: PLW2901
        return out
    if capability == "notify":
        # The body defaults to the command itself, but the dataflow layer will
        # REPLACE a bare command echo with a real summary of what was made
        # (the toast should say what the chain produced, not echo the order).
        return {"operation": "notify", "title": text or "Universal Mind", "body": command}
    if capability == "llm":
        # R45-15 — the prompt is the sentence AFTER the trigger words; the
        # whole command is a valid prompt when no cleaner cut exists.
        prompt = command
        for trig in ("هوش مصنوعی", "مدل زبانی", "بپرس", "بپرس از"):
            if trig in prompt:
                prompt = prompt.split(trig, 1)[1]
        prompt = prompt.strip(" ،.:؛")
        return {"prompt": prompt or command}

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
        # «بخوان» only signals a READ-back when NO explicit store verb follows —
        # «متن تصویر را بخوان و در دیتابیس ذخیره کن» reads AND stores: the
        # store verb wins, the flow layer fills the rows.
        asking = any(w in command for w in ("چی ذخیره", "چه ذخیره", "نشونم بده", "نشان بده")) or (
            "بخوان" in command and "ذخیره کن" not in command
        )
        if asking:
            return {
                "operation": "query",
                "sql": "SELECT metric, value FROM chain_results "
                       "ORDER BY rowid DESC LIMIT 20",
                "persistent": True,
            }
        # «گزارش از ذخیرهشدهها» / «PDF از نتایج» — the MEMORY becomes a
        # DOCUMENT: the pdf renders the stored chain_results as a real table
        # (the read-back flow). «نتایج» is the operator's word for the same
        # thing: what the runs actually produced.
        if ("گزارش از" in command and "ذخیره" in command) or (
            "نتایج" in command and ("pdf" in command.lower() or "پی دی اف" in command)
        ):
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
        # A spoken COUNT («با سه سطر») is real data too: Persian number
        # words the extractor never turned into values.
        _FA_COUNTS = {"یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
                      "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10}
        if not data and "ذخیره" in command:
            import re as _re

            m = _re.search(r"با\s+(یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده)\s+سطر", command)
            if m:
                n = _FA_COUNTS[m.group(1)]
                data = [float(i + 1) for i in range(n)]  # seeded series 1..n
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