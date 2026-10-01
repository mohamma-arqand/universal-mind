"""THE UNIT-CONVERT TOOL — the platform converts what the operator measures.

R59 P2. The sweep measured two real sentences dying in «نشناختم»:
«۱۰ کیلومتر چند مایل است؟» and «۱۰۰ فارنهایت چند سانتیگراد است؟».

Laws (the house style):
  - Every conversion is an EXPLICIT factor or formula in a table — never a
    guessed constant, never an import of a third-party unit library.
  - Temperature is a FORMULA (linear), not a factor — 0°C is 32°F, and any
    factor table would silently get that wrong.
  - Unknown or mismatched units are refused BY NAME with the list of known
    units, never defaulted.
  - The answer is Persian through and through: Persian digits, the source and
    target units, and the recipe when something is missing.
"""

from __future__ import annotations

import re
from typing import Any

# length (base: meters)
_LENGTH: dict[str, float] = {
    "میلی‌متر": 0.001, "سانتی‌متر": 0.01, "متر": 1.0,
    "کیلومتر": 1000.0, "اینچ": 0.0254, "فوت": 0.3048, "یارد": 0.9144,
    "مایل": 1609.344, "مایل دریایی": 1852.0,
}
# mass (base: kilograms)
_MASS: dict[str, float] = {
    "گرم": 0.001, "کیلوگرم": 1.0, "کیلو": 1.0, "پوند": 0.45359237,
    "اونس": 0.028349523125, "تن": 1000.0,
}
# data (base: bytes)
_DATA: dict[str, float] = {
    "بایت": 1.0, "کیلوبایت": 1024.0, "مگابایت": 1024.0 ** 2,
    "گیگابایت": 1024.0 ** 3, "ترابایت": 1024.0 ** 4,
}
# time (base: seconds)
_TIME: dict[str, float] = {
    "میلی‌ثانیه": 0.001, "ثانیه": 1.0, "دقیقه": 60.0, "ساعت": 3600.0,
    "روز": 86400.0, "هفته": 604800.0,
}
_FAMILIES: list[tuple[str, dict[str, float]]] = [
    ("طول", _LENGTH), ("وزن", _MASS), ("حجم داده", _DATA), ("زمان", _TIME),
]
# temperature: formula pairs, not factors
_TEMPS = ("سانتیگراد", "سلسیوس", "فارنهایت", "کلوین")

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(value: object) -> str:
    return str(value).translate(_FA)


def _all_units() -> list[str]:
    units: list[str] = []
    for _, table in _FAMILIES:
        units.extend(table)
    units.extend(_TEMPS)
    return units


def _family_of(unit: str) -> tuple[str, dict[str, float]] | None:
    for fam, table in _FAMILIES:
        if unit in table:
            return fam, table
    return None


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_UNIT_RE = re.compile(
    r"(میلی‌متر|میلی‌متر|سانتی‌متر|سانتیگراد|سلسیوس|فارنهایت|کلوین|کیلومتر|کیلوگرم|"
    r"کیلوبایت|مگابایت|گیگابایت|ترابایت|میلی‌ثانیه|مایل دریایی|کیلو|پوند|گرم|اینچ|فوت|یارد|"
    r"مایل|اونس|تن|متر|ثانیه|دقیقه|ساعت|روز|هفته|بایت)"
)


def convert(value: float, source: str, target: str) -> dict[str, Any]:
    """Convert a real value between two units — or refuse by name."""
    src, tgt = source.strip(), target.strip()
    if src not in _all_units():
        return {"ok": False, "error": f"واحد «{src}» را نمی‌شناسم — واحدهای شناخته: "
                                      f"{_fa(len(_all_units()))} واحد", "known": _all_units()}
    if tgt not in _all_units():
        return {"ok": False, "error": f"واحد «{tgt}» را نمی‌شناسم — واحدهای شناخته: "
                                      f"{_fa(len(_all_units()))} واحد", "known": _all_units()}

    # temperature: its own formula family
    if src in _TEMPS or tgt in _TEMPS:
        if src not in _TEMPS or tgt not in _TEMPS:
            return {"ok": False, "error": f"«{src}» و «{tgt}» از یک خانواده نیستند — "
                                          "دما فقط با دما تبدیل می‌شود"}
        c = _to_celsius(value, src)
        out = _from_celsius(c, tgt)
        return {"ok": True, "value": out, "source": src, "target": tgt,
                "family": "دما", "error": ""}

    fam_src, tbl_src = _family_of(src) or ("", {})
    fam_tgt, tbl_tgt = _family_of(tgt) or ("", {})
    if fam_src != fam_tgt or not fam_src:
        return {"ok": False, "error": f"«{src}» ({fam_src or 'نامعلوم'}) و «{tgt}» "
                                      f"({fam_tgt or 'نامعلوم'}) از یک خانواده نیستند"}
    base = value * tbl_src[src]
    out = base / tbl_tgt[tgt]
    return {"ok": True, "value": out, "source": src, "target": tgt,
            "family": fam_src, "error": ""}


def _to_celsius(value: float, unit: str) -> float:
    if unit in ("سانتیگراد", "سلسیوس"):
        return value
    if unit == "فارنهایت":
        return (value - 32.0) * 5.0 / 9.0
    if unit == "کلوین":
        return value - 273.15
    return value


def _from_celsius(c: float, unit: str) -> float:
    if unit in ("سانتیگراد", "سلسیوس"):
        return c
    if unit == "فارنهایت":
        return c * 9.0 / 5.0 + 32.0
    if unit == "کلوین":
        return c + 273.15
    return c


def parse_convert_request(command: str) -> dict[str, Any] | None:
    """«۱۰ کیلومتر چند مایل است؟» → {value, source, target}, or None.

    None means the sentence is not a conversion — the caller moves on and the
    router stays honest.
    """
    if "چند" not in command and "تقریبا" not in command:
        return None
    m_num = _NUM_RE.search(command)
    units = _UNIT_RE.findall(command)
    if not m_num or len(units) < 2:
        return None
    return {"value": float(m_num.group(0)), "source": units[0], "target": units[1]}


def convert_fa(value: float, source: str, target: str) -> str:
    """The Persian answer to a conversion, ready for the operator's report."""
    out = convert(value, source, target)
    if not out.get("ok"):
        return str(out.get("error"))
    v = out["value"]
    shown = f"{v:.4f}".rstrip("0").rstrip(".")
    # the SOURCE value is Persianized too (a Latin digit or a bare .0 in the
    # operator's report is a leak): 100.0 → ۱۰۰
    src_shown = f"{value:.4f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    return (f"{_fa(src_shown)} {source} برابر است با {_fa(shown)} {target}"
            f" ({out['family']}).")


class UnitConvertToolConnector:
    """Adapts the converter to the ``Connector`` protocol."""

    name = "unitconvert"
    capability = "unitconvert"

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "convert") or "convert"
        if operation != "convert":
            return ConnectorResult(ok=False, output=None,
                                    error=f"unknown operation: {operation!r}")
        value = params.get("value")
        source = str(params.get("source", ""))
        target = str(params.get("target", ""))
        if value is None or not source or not target:
            return ConnectorResult(
                ok=False, output=None,
                error="چه چیزی را به چه چیزی؟ مثلا: ۱۰ کیلومتر چند مایل است؟",
            )
        try:
            out = convert(float(value), source, target)
        except (TypeError, ValueError) as exc:
            return ConnectorResult(ok=False, output=None, error=str(exc))
        if not out.get("ok"):
            return ConnectorResult(ok=False, output=None, error=str(out["error"]))
        return ConnectorResult(ok=True, output={
            k: v for k, v in out.items() if k not in ("ok", "error")
        } | {"answer_fa": convert_fa(float(value), source, target)}, error="")


__all__ = ["UnitConvertToolConnector", "convert", "convert_fa", "parse_convert_request"]
