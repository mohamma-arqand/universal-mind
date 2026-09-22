"""Persian reporter — the run's result as fluent Persian sentences.

The engine's payloads are JSON with English keys (data/chart/mean/bytes...).
This module renders them as human Persian: «میانگین ۳ عدد برابر ۴ شد»، «نمودار
خطی ساخته شد (۲۴ کیلوبایت)»، «۳ ردیف در دیتابیس ذخیره شد». It reads only what
the real run produced — a missing field is skipped honestly, never invented.

Deterministic and pure: a given payload always renders the same report.
"""

from __future__ import annotations

from typing import Any

# Persian labels for the capability names (single source for rendering).
_VIRTUE_FA: dict[str, str] = {
    "wisdom": "حکمت",
    "courage": "شهامت",
    "temperance": "اعتدال",
    "justice": "عدالت",
}

_CAP_FA: dict[str, str] = {
    "data": "تحلیل داده",
    "ai": "یادگیری ماشین",
    "vision": "بینایی کامپیوتر",
    "chart": "نمودار",
    "pdf": "سند PDF",
    "image": "پردازش تصویر",
    "media": "رسانه",
    "archive": "فشردهسازی",
    "compute": "محاسبه",
    "database": "دیتابیس",
    "notify": "اطلاعرسانی",
    "clipboard": "کلیپبورد",
    "speech": "گفتار",
    "ocr": "متنخوان",
    "excel": "صفحهگسترده",
    "webfetch": "وب",
    "pdfreader": "خوانندهی PDF",
    "screenshot": "عکس صفحه",
    "goal": "عامل هدف",
}

_CHART_KIND_FA: dict[str, str] = {
    "line": "خطی", "bar": "میله", "barh": "میله افقی", "pie": "دایرهای",
    "histogram": "هیستوگرام", "hist2d": "هیستوگرام دوبعدی", "scatter": "پراکنده",
    "boxplot": "جعبهای", "violin": "ویولن", "stackplot": "ناحیه انباشته",
    "step": "پلهای", "contour": "کانتور", "errorbar": "نوار خطا",
    "fill_between": "نوار پر",
}


def _fa_num(value: float | str) -> str:
    """A number with Persian digits and trimmed decimals.

    A ``str`` is parsed as a number when possible (stored values come back
    from SQLite as text); a non-numeric label is returned as-is.
    """
    # A stored value may come back as a numeric STRING ('12', '3.266') —
    # parse it first so fresh and stored numbers render identically.
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return str(value)  # a genuine label, not a number — render as-is
    if isinstance(value, int):
        text = str(value)
    elif value == int(value):
        text = str(int(value))
    else:
        text = str(round(value, 4))
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _kb(bytes_value: Any) -> str:
    try:
        n = int(bytes_value)
    except (TypeError, ValueError):
        return "—"
    if n >= 1024:
        return f"{_fa_num(round(n / 1024, 1))} کیلوبایت"
    return f"{_fa_num(n)} بایت"


def _sentence_data(result: dict[str, Any]) -> str:
    mean = result.get("mean")
    if mean is None:
        return "تحلیل انجام شد."
    count = result.get("count", 0)
    parts = [f"میانگین {_fa_num(count)} عدد برابر {_fa_num(mean)}"]
    if result.get("std") is not None:
        parts.append(f"انحراف معیار {_fa_num(result['std'])}")
    if result.get("max") is not None and result.get("min") is not None:
        parts.append(f"از {_fa_num(result['min'])} تا {_fa_num(result['max'])}")
    return "، ".join(parts) + " شد."


def _sentence_ai(result: dict[str, Any]) -> str:
    if "accuracy" in result:
        return f"مدل با دقت {_fa_num(round(result['accuracy'] * 100, 1))}٪ آموزش دید."
    if "coefficients" in result:
        coeffs = result["coefficients"]
        return f"مدل رگرسیون با {len(coeffs)} ضریب آموزش دید (ضریب اول {_fa_num(coeffs[0])})."
    if "centroids" in result:
        return f"خوشهبندی {_fa_num(len(result['centroids']))} خوشه پیدا کرد."
    if "dominant_frequencies" in result:
        freqs = result["dominant_frequencies"]
        return f"تبدیل فوریه فرکانس غالب {_fa_num(freqs[0])} را کشف کرد."
    return "یادگیری ماشین انجام شد."


def _sentence_vision(result: dict[str, Any]) -> str:
    # A structure read (chart_structure) narrates UNDERSTANDING, not pixels.
    if "dominant_colors" in result:
        colors = result.get("dominant_colors") or []
        lines_n = result.get("long_lines", 0)
        ink = result.get("ink_ratio", 0.0)
        if colors:
            top = colors[0]
            share = top.get("share", 0.0)
            return (
                f"ساختار تصویر خوانده شد: {_fa_num(lines_n)} خطِ بلند شناسایی شد، "
                f"رنگِ غالب {_fa_num(round(share * 100))}٪ کانوس را پوشانده، "
                f"تراکم جوهر {_fa_num(round(ink * 100, 1))}٪."
            )
        return f"ساختار تصویر خوانده شد: {_fa_num(lines_n)} خطِ بلند."
    if "edge_pixels" in result:
        return f"{_fa_num(result['edge_pixels'])} پیکسل لبه پیدا شد."
    if "contour_count" in result:
        areas = result.get("largest_areas", [])
        biggest = f" (بزرگترین: {_fa_num(areas[0])})" if areas else ""
        return f"{_fa_num(result['contour_count'])} ناحیه در تصویر پیدا شد{biggest}."
    if "white_ratio" in result:
        return f"{_fa_num(round(result['white_ratio'] * 100, 1))}٪ از تصویر روشن است."
    if "shape" in result:
        return f"تصویر {_fa_num(result['shape'][0])}×{_fa_num(result['shape'][1])} پیکسل است."
    return "تحلیل تصویر انجام شد."


def _render_capability(cap: str, result: Any, params: dict[str, Any] | None) -> str | None:
    """One fluent Persian sentence for one capability's real result (or None)."""
    name = _CAP_FA.get(cap, cap)
    if cap == "compute" and isinstance(result, (int, float)):
        return f"محاسبه انجام شد: نتیجه {_fa_num(result)}."
    if not isinstance(result, dict):
        # A database read-back is a LIST of rows — fall through so the
        # database branch can narrate it (everything else needs a dict).
        if not (cap == "database" and isinstance(result, list)):
            return None
    if cap == "data":
        return _sentence_data(result)
    if cap == "ai":
        return _sentence_ai(result)
    if cap == "vision":
        return _sentence_vision(result)
    if cap == "chart":
        kind = _CHART_KIND_FA.get((params or {}).get("operation", "line"), "")
        kind_fa = f" {kind}" if kind else ""
        return f"نمودار{kind_fa} ساخته شد ({_kb(result.get('bytes'))})."
    if cap == "pdf":
        return f"سند PDF ساخته شد ({_kb(result.get('bytes'))})."
    if cap == "goal" and isinstance(result, dict):
        # The agent's own run report — the step verdicts narrated as one goal.
        report_text = str(result.get("report", ""))
        if report_text:
            steps_done = int(result.get("steps", 0))
            finished = bool(result.get("finished"))
            head = "🎯 هدف" if finished else "🎯 هدف (ناتمام)"
            return f"{head} — {_fa_num(steps_done)} گام داوری شد.\n{report_text}"
        return "هدف اجرا شد."
    if cap == "screenshot" and isinstance(result, dict):
        if result.get("path"):
            return (
                f"از صفحه عکس گرفته شد ({_fa_num(int(result.get('width') or 0))}×"
                f"{_fa_num(int(result.get('height') or 0))} "
                f"پیکسل، {_kb(result.get('bytes'))})."
            )
        return None
    if cap == "webfetch" and isinstance(result, dict):
        title = str(result.get("title", ""))
        status = result.get("status")
        if title:
            return f"صفحهی وب گرفته شد (کد {status}): «{title}» ({_kb(result.get('bytes'))})."
        return f"صفحهی وب گرفته شد (کد {status})."
    if cap == "pdfreader" and isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        pages = result.get("pages", 0)
        if text:
            preview = text[:50] + ("…" if len(text) > 50 else "")
            return f"PDF خوانده شد ({_fa_num(pages)} صفحه): «{preview}»"
        return f"PDF خوانده شد ({_fa_num(pages)} صفحه) — لایهی متنی ندارد (اسکن است؟)"
    if cap == "excel" and isinstance(result, dict):
        if "rows" in result:  # a write: a real workbook was made
            return (
                f"صفحهگستردهی اکسل ساخته شد "
                f"({_fa_num(result['rows'])} ردیف × {_fa_num(result['columns'])} ستون، {_kb(result.get('bytes'))})."
            )
        if "headers" in result:  # a read: a real workbook came back
            return (
                f"صفحهگسترده خوانده شد: {_fa_num(len(result.get('rows', [])))} ردیف "
                f"با ستونهای {'، '.join(str(h) for h in result.get('headers', []))}."
            )
        return None
    if cap == "ocr" and isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        lang = str(result.get("language", ""))
        if text:
            preview = text[:40] + ("…" if len(text) > 40 else "")
            return f"متنِ تصویر خوانده شد ({lang}): «{preview}»"
        return "تصویر خوانده شد — متنی در آن پیدا نشد."
    if cap == "speech" and isinstance(result, dict):
        if result.get("spoken"):
            voice = result.get("voice", "")
            return f"با صدای واقعی گفته شد (صدا: {voice})."
        # R41: the honest blocked-env answer carries the REMEDY, not just
        # the refusal — the operator learns the exact fix in the chat.
        err = str(result.get("error", ""))
        if "صدای فارسی" in err:
            return "بلند نشد: صدای فارسی روی این ویندوز نصب نیست. از Settings > Time & Language > Speech صدای fa-IR را نصب کن تا بلندخوانی کار کند."
        return None  # failures render via the honest error line
    if cap == "database" and isinstance(result, list):
        # The read-back: real stored rows narrated as Persian memory.
        if not result:
            return "دیتابیس را خواندم — هنوز چیزی ذخیره نشده."
        fa_metric = {
            "mean": "میانگین", "std": "انحراف معیار", "min": "کمینه", "max": "بیشینه",
            "median": "میانه", "count": "تعداد", "value": "مقدار",
        }
        parts = []
        for row in result[:5]:
            if not isinstance(row, dict):
                continue
            metric = str(row.get("metric", "?"))
            fa = fa_metric.get(metric, metric)
            parts.append(f"{fa}={_fa_num(str(row.get('value', '')))}")
        more = f" (و {_fa_num(len(result) - 5)} مورد دیگر)" if len(result) > 5 else ""
        return f"دیتابیس را خواندم — آخرین ذخیرهها: {'، '.join(parts)}{more}."
    if cap == "archive":
        return f"آرشیو فشرده ساخته شد ({_kb(result.get('bytes'))})."
    if cap == "compute":
        return f"محاسبه انجام شد: نتیجه {_fa_num(result) if isinstance(result, (int, float)) else 'آماده'}."
    if cap == "database":
        if result.get("inserted") is not None:
            return f"{_fa_num(result['inserted'])} ردیف در دیتابیس ذخیره شد."
        rows: list[Any] = result if isinstance(result, list) else []
        return f"{_fa_num(len(rows))} ردیف از دیتابیس خوانده شد."
    if cap == "notify":
        return "اطلاعرسانی ویندوز نمایش داده شد."
    if cap == "clipboard":
        return "کلیپبورد ویندوز بهروزرسانی شد."
    if cap == "media":
        return f"رسانه تولید شد ({_kb(result.get('bytes'))})."
    if cap == "image":
        if "format" in result:
            return f"تصویر {result.get('format')} بررسی شد."
        return f"پردازش تصویر انجام شد ({_kb(result.get('bytes'))})."
    return f"{name} انجام شد."


def persian_report(payload: dict[str, Any]) -> str:
    """Render a full Persian, human-readable report of one run.

    Reads the SAME payload route_and_run returns: the route, the per-capability
    results, and the errors. Unknown capabilities are rendered generically; a
    failed capability renders its honest failure. Never invents a value.
    """
    if not payload.get("ok") and not payload.get("result"):
        # R41: the honest answer NAMED — a capability error beats a vague
        # 'علت نامشخص' (the speech blocked-env refusal was being swallowed).
        error = payload.get("error") or "; ".join(
            str(e) for e in (payload.get("errors") or {}).values()
        ) or "علت نامشخص"
        return f"❌ اجرا ناموفق بود: {error}"

    route: list[str] = list(payload.get("route", []))
    results: dict[str, Any] = payload.get("result", {}) or {}
    params: dict[str, Any] = payload.get("extracted_params", {}) or {}
    errors: dict[str, str] = payload.get("errors", {}) or {}

    lines: list[str] = []
    chain_fa = " ← ".join(_CAP_FA.get(c, c) for c in route)
    lines.append(f"✅ اجرا انجام شد: {chain_fa}")

    # The dataflow — when one program's output became the next program's input,
    # the report SAYS SO (the fusion is the whole point, it must be visible).
    # Capability names inside the flow are rendered in Persian (no English leak).
    flows: list[str] = list(payload.get("flows", []) or [])
    for flow in flows:
        rendered = flow
        # Longest English name FIRST — 'database' before 'data' (a prefix
        # translate of 'data' would corrupt 'database' into 'تحلیل دادهbase').
        for en, fa in sorted(_CAP_FA.items(), key=lambda kv: -len(kv[0])):
            rendered = rendered.replace(f" {en} ", f" {fa} ")
            rendered = rendered.replace(f"→ {en}", f"→ {fa}")
            rendered = rendered.replace(f"{en} →", f"{fa} →")
        # Persian digits inside the flow line too (a Latin '1' is a leak).
        rendered = rendered.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        lines.append(f"🔗 {rendered}")

    # R44-7 — THE A/B RULING: an ambiguous kind ran as a real contest; the
    # report announces the winner and the margin (the ruling is visible).
    ab_ruling = payload.get("ab_ruling")
    if ab_ruling:
        lines.append(f"⚖ {ab_ruling}")

    # ARETĒ's judgment of this very run — the virtues computed from its own data.
    judgment: dict[str, Any] = payload.get("judgment") or {}
    if judgment and not judgment.get("disqualified", False):
        scores = judgment.get("scores", {})
        shown = ", ".join(
            f"{_VIRTUE_FA.get(name, name)} {_fa_num(score)}"
            for name, score in scores.items()
        )
        lines.append(f"🏛 داوری ARETĒ: {shown}")
    elif judgment:
        reason = str(judgment.get("disqualify_reason", ""))
        lines.append(f"🏛 داوری ARETĒ: رد شد ({reason})")

    for cap in route:
        if cap in errors:
            lines.append(f"• {_CAP_FA.get(cap, cap)}: ناموفق ({errors[cap]})")
            continue
        sentence = _render_capability(cap, results.get(cap), params.get(cap))
        if sentence:
            lines.append(f"• {sentence}")

    # R44-5 — THE CROSS-EXAMINER'S VOICE: when a numeric verdict ran twice
    # (numpy + independent pure-Python), the report SAYS SO — agreement is a
    # second signature; disagreement is a caught bug, named.
    for cap in route:
        res = results.get(cap)
        if isinstance(res, dict) and isinstance(res.get("cross_exam"), dict):
            from universal_mind.cross_examiner import persian_note

            note = persian_note(res["cross_exam"])
            if note:
                lines.append(f"• {note}")

    # The fusion detail for pdf: WHAT flowed into the report (chart or stats table).
    pdf_flows = [f for f in flows if "→ pdf" in f]
    if pdf_flows and "نمودار درونش" in pdf_flows[0]:
        lines.append("• گزارش فارسی با نمودارِ همین اجرا درونش ساخته شد.")
    elif pdf_flows and "جدول آمار" in pdf_flows[0]:
        lines.append("• گزارش فارسی با جدولِ آمارِ همین اجرا درونش ساخته شد.")
    # The perception detail for notify: the toast said what the chain MADE.
    notify_flow = next((f for f in flows if "→ notify" in f), None)
    if notify_flow and "→ notify (" in notify_flow:
        summary = notify_flow.split("→ notify (", 1)[1].rstrip(")")
        lines.append(f"• اعلان ویندوز نشان داده شد: «{summary}»")
    # The preservation detail for archive: everything made, packed together.
    archive_flow = next((f for f in flows if "→ archive" in f), None)
    if archive_flow:
        lines.append("• همهی خروجیهای این اجرا در یک بایگانی یکجا بستهبندی شد.")
    # The perception detail for vision: the chain's own image, understood.
    vision_flow = next((f for f in flows if "→ بینایی" in f or "→ vision" in f), None)
    if vision_flow:
        lines.append("• سیستم تصویری را که خودش ساخت، با بینایی ماشین تحلیل کرد.")
    # The persistence detail for database: computed results stored, named.
    database_flow = next((f for f in flows if "→ database" in f), None)
    if database_flow and "→ database (" in database_flow:
        detail = database_flow.split("→ database (", 1)[1].rstrip(")")
        lines.append(f"• نتایج محاسبهشده در دیتابیس ذخیره شد ({detail}).")
    # The hand-over detail for clipboard: what was made is ready to paste.
    clipboard_flow = next((f for f in flows if "→ clipboard" in f), None)
    if clipboard_flow and "→ clipboard (" in clipboard_flow:
        summary = clipboard_flow.split("→ clipboard (", 1)[1].rstrip(")")
        lines.append(f"• خلاصه در کلیپبورد ویندوز قرار گرفت: «{summary}»")

    return "\n".join(lines)


__all__ = ["persian_report"]