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
}

_CHART_KIND_FA: dict[str, str] = {
    "line": "خطی", "bar": "میله", "barh": "میله افقی", "pie": "دایرهای",
    "histogram": "هیستوگرام", "hist2d": "هیستوگرام دوبعدی", "scatter": "پراکنده",
    "boxplot": "جعبهای", "violin": "ویولن", "stackplot": "ناحیه انباشته",
    "step": "پلهای", "contour": "کانتور", "errorbar": "نوار خطا",
    "fill_between": "نوار پر",
}


def _fa_num(value: float) -> str:
    """A number with Persian digits and trimmed decimals."""
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
        error = payload.get("error", "علت نامشخص")
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
    flows: list[str] = list(payload.get("flows", []) or [])
    if flows:
        for flow in flows:
            lines.append(f"🔗 {flow}")

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

    # The fusion detail for pdf: WHAT flowed into the report (chart or stats table).
    pdf_flows = [f for f in flows if "→ pdf" in f]
    if pdf_flows and "نمودار درونش" in pdf_flows[0]:
        lines.append("• گزارش فارسی با نمودارِ همین اجرا درونش ساخته شد.")
    elif pdf_flows and "جدول آمار" in pdf_flows[0]:
        lines.append("• گزارش فارسی با جدولِ آمارِ همین اجرا درونش ساخته شد.")

    return "\n".join(lines)


__all__ = ["persian_report"]