"""Tests for Persian temporal resolution — «امروز» becomes the real Jalali date."""

from __future__ import annotations

from datetime import datetime, timezone

from universal_mind.persian_date import (
    jalali_date,
    resolve_temporal,
    with_resolved_date,
)


def test_today_is_a_real_jalali_date() -> None:
    frozen = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    date = jalali_date(0, now=frozen)
    # 2026-09-15 Gregorian is 1405/06/24 Jalali.
    assert date.startswith("۱۴۰۵")
    assert "/" in date
    assert any(ch in date for ch in "۰۱۲۳۴۵۶۷۸۹")


def test_yesterday_is_one_day_before() -> None:
    frozen = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    today = jalali_date(0, now=frozen)
    yesterday = jalali_date(-1, now=frozen)
    assert yesterday != today


def test_resolve_temporal_words() -> None:
    frozen = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    assert resolve_temporal("گزارش امروز را بساز", now=frozen) == jalali_date(0, now=frozen)
    assert resolve_temporal("گزارش دیروز", now=frozen) == jalali_date(-1, now=frozen)
    assert resolve_temporal("گزارش پریروز", now=frozen) == jalali_date(-2, now=frozen)
    # No temporal word -> no invented date.
    assert resolve_temporal("گزارش ماه", now=frozen) is None


def test_with_resolved_date_attaches_only_when_said() -> None:
    frozen = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    resolved = with_resolved_date("گزارش", "گزارش امروز", now=frozen)
    assert "گزارش" in resolved and "امروز" not in resolved and "۱۴۰۵" in resolved
    assert with_resolved_date("گزارش", "گزارش ماه", now=frozen) == "گزارش"
    assert with_resolved_date(None, "گزارش امروز", now=frozen) is None


def test_end_to_end_pdf_title_carries_real_date() -> None:
    """A quoted title with «امروز» -> the pdf title carries the real Jalali date."""
    from universal_mind.persian_params import extract_params

    params = extract_params('گزارش «امروز» را بساز', "pdf")
    title = params["title"]
    assert "امروز" not in title  # the literal word is resolved away
    assert "۱۴۰۵" in title  # the real Jalali year
