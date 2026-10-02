"""Persian temporal expressions — «امروز» / «دیروز» become real dates.

A command like «گزارش امروز را بساز» should carry the ACTUAL current date (in the
Persian calendar) in the document title, not the literal word "امروز". This module
resolves temporal words against a real clock:

- «امروز»  → today's Jalali date (e.g. ۱۴۰۴/۰۶/۲۲);
- «دیروز»  → yesterday's Jalali date;
- «پریروز» → two days ago.

Deterministic given the clock: a frozen clock yields a frozen date.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """The standard Gregorian→Jalali conversion (algorithm by JDF)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_date(offset_days: int = 0, *, now: datetime | None = None) -> str:
    """The Jalali date for today (+offset), formatted ۱۴۰۴/۰۶/۲۲ with Persian digits."""
    if now is None:
        now = datetime.now(timezone.utc)
    moment = now + timedelta(days=offset_days)
    jy, jm, jd = _gregorian_to_jalali(moment.year, moment.month, moment.day)
    fa_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return f"{jy}/{jm:02d}/{jd:02d}".translate(fa_digits)


def gregorian_to_jalali_parts(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """R61-S1 — public wrapper: (jy, jm, jd) for a Gregorian date.

    The clock answer used to glue the GREGORIAN day number to a JALALI
    month name («امروز ۲ دی» in October — two calendars in one sentence);
    callers need the real Jalali parts, not a private helper.
    """
    return _gregorian_to_jalali(gy, gm, gd)


def resolve_temporal(command: str, *, now: datetime | None = None) -> str | None:
    """A temporal word in the command («امروز»/«دیروز»/«پریروز») → a real Jalali date.

    Returns None when the command carries no temporal word — no date is invented.
    """
    # «پریروز» must be checked before «دیروز» (it contains it as a substring).
    if "پریروز" in command:
        return jalali_date(-2, now=now)
    if "دیروز" in command:
        return jalali_date(-1, now=now)
    if "امروز" in command:
        return jalali_date(0, now=now)
    return None


def with_resolved_date(text: str | None, command: str, *, now: datetime | None = None) -> str | None:
    """Replace the temporal word in the title WITH the resolved Jalali date.

    «گزارش امروز» → «گزارش — ۱۴۰۵/۰۶/۲۴»: the literal word «امروز» is resolved
    away, not merely appended to. When the command says no time, the text passes
    through unchanged; a None text stays None (no date invented from nothing).
    """
    if text is None:
        return None
    date = resolve_temporal(command, now=now)
    if date is None:
        return text
    cleaned = text
    for word in ("پریروز", "دیروز", "امروز"):
        cleaned = cleaned.replace(word, "").replace("  ", " ").strip(" —-")
    if not cleaned:
        return date
    return f"{cleaned} — {date}"


__all__ = ["jalali_date", "resolve_temporal", "with_resolved_date"]