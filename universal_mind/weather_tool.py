"""R79 B4 — WEATHER: the real thing (open-meteo), cached and honest.

The audit refused «هوا چطوره؟» with «دادهٔ بیرونی میخواهد» while the
machine WAS online — because nothing asked the sky. Weather is now the
33rd real capability:

  * LIVE: open-meteo (no key, no signup — the one public API that works
    from this machine as-is). The city resolves from a real, shipped
    gazetteer (data/cities_fa.json: the top ~30 Iranian cities + a few
    world capitals) — «هوای شیراز» finds 29.59, 52.58.
  * CACHED: every successful fetch is kept with its timestamp. A later
    ask inside the freshness window answers from the cache and SAYS SO
    («دادهٔ ۱۲ دقیقه پیش»); a stale/offline ask that HAS an old sample
    answers with it, NAMED as old («آخرین دادهٔ دارم از ۳ ساعت پیش
    است…»). Never presented as fresh, never fabricated.
  * OFFLINE WITH NO SAMPLE: the honest refusal (the R62 recipe) — named
    reason + the two real roads (connect/proxy).
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

_GAZETTEER = Path(__file__).resolve().parent / "data" / "cities_fa.json"
_CACHE_TTL_S = 30 * 60  # 30 min: weather changes slower than that
_FRESH_WINDOW_S = 15 * 60

_code_map = {
    0: "آسمان صاف", 1: "بیشتر صاف", 2: "نیمهابری", 3: "ابری",
    45: "مه", 48: "مهی یخزده", 51: "نمبارانِ سبک", 53: "نمباران",
    55: "نمبارانِ سنگین", 61: "بارانِ سبک", 63: "باران", 65: "بارانِ سنگین",
    71: "برفِ سبک", 73: "برف", 75: "برفِ سنگین", 80: "رگبارِ سبک",
    81: "رگبار", 82: "رگبارِ شدید", 95: "رعدوبرق",
    96: "رعدوبرق با تگرگ", 99: "رعدوبرق با تگرگِ سنگین",
}


def _load_cities() -> dict[str, list[float]]:
    try:
        return json.loads(_GAZETTEER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cache_path(city: str) -> Path:
    home = Path.home() / ".universal-mind"
    home.mkdir(parents=True, exist_ok=True)
    return home / "weather_cache.json"


def _read_cache() -> dict[str, dict[str, Any]]:
    try:
        return json.loads(_cache_path("").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_cache(cache: dict[str, dict[str, Any]]) -> None:
    try:
        _cache_path("").write_text(
            json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # a read-only home still works live-only


def _describe(code: int) -> str:
    return _code_map.get(code, f"کدِ وضعیت {code}")


def _fa_num(x: object) -> str:
    return str(x).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def weather(city: str) -> dict[str, Any]:
    """The real weather for a city, cached and honestly labelled."""
    key = (city or "").strip() or "تهران"
    cities = _load_cities()
    coords = cities.get(key) or cities.get(_norm_fa(key))
    if coords is None:
        known = "، ".join(sorted(cities)[:12])
        return {"ok": False, "error": (
            f"شهرِ «{key}» در فهرستِ شهرهای من نیست. شهرهای شناختهشده: "
            f"{known} و…")}

    cache = _read_cache()
    hit = cache.get(key)
    now = time.time()

    live: dict[str, Any] | None = None
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}"
               f"&longitude={coords[1]}&current_weather=true"
               f"&timezone=auto")
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            live = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError):
        live = None

    if live is not None:
        cw = live.get("current_weather", {})
        entry = {
            "city": key, "fetched_at": now,
            "temp_c": cw.get("temperature"),
            "wind_kmh": cw.get("windspeed"),
            "code": cw.get("weathercode"),
            "desc": _describe(int(cw.get("weathercode", -1))),
            "is_day": bool(cw.get("is_day", 1)),
        }
        cache[key] = entry
        _write_cache(cache)
        return {"ok": True, "source": "live", **entry}

    # offline path — the cache decides between "stale-but-named" and refusal
    if hit and now - float(hit.get("fetched_at", 0)) < 24 * 3600:
        age_min = int((now - float(hit["fetched_at"])) // 60)
        return {"ok": True, "source": "cache", "age_min": age_min, **hit,
                "note": (f"اینترنت نبود؛ آخرین دادهٔ دارم از "
                         f"{_fa_num(age_min)} دقیقه پیش است.")}
    return {"ok": False, "error": (
        "به منبعِ هواشناسی وصل نشدم و دادهٔ کششدهٔ تازه هم ندارم — حدس "
        "نمیزنم. دو راه: اینترنت/پروکسی را وصل کن، یا بعداً دوباره بپرس.")}


def _norm_fa(s: str) -> str:
    return (s.replace("ی", "ی").replace("ك", "ک")
             .replace("\u200c", " ").strip())


__all__ = ["weather"]
