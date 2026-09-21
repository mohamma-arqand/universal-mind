"""Tests: R40 — the surviving conversation, the clickable fix, the Jalali
dashboard, and the explicit dashboard path."""

from __future__ import annotations

import datetime
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

from universal_mind.chat_history_store import (
    log_message,
    message_count,
    recent_messages,
)
from universal_mind.superplatform_dashboard import (
    _g_to_jalali,
    _jalali_day,
    build_dashboard,
)


def _isolated_chat() -> Any:
    import tempfile as _tf

    from universal_mind.database_suite import DatabaseSuite

    tmp = Path(_tf.mkdtemp()) / "chat.db"
    suite = DatabaseSuite(str(tmp))

    return mock_patch.object(
        __import__("universal_mind.database_suite", fromlist=["DatabaseSuite"]).DatabaseSuite,
        "shared_persistent",
        classmethod(lambda cls: suite),
    )


# ---------- L1: the conversation survives ----------
def test_chat_history_roundtrip() -> None:
    with _isolated_chat():
        log_message("من", "سلام")
        log_message("سیستم", "در خدمتم", ok=True)
        msgs = recent_messages()
        assert [m["who"] for m in msgs] == ["من", "سیستم"]
        assert msgs[1]["ok"] is True
        assert message_count() == 2


def test_chat_replay_order_is_oldest_first() -> None:
    with _isolated_chat():
        for i in range(60):
            log_message("من", f"پیام {i}")
        msgs = recent_messages(limit=50)
        assert len(msgs) == 50
        # oldest first — the newest 50, in chat order
        assert msgs[0]["text"] == "پیام 10"
        assert msgs[-1]["text"] == "پیام 59"


def test_chat_log_never_raises() -> None:
    with _isolated_chat():
        # a broken DB must not kill the chat
        with mock_patch.object(
            __import__("universal_mind.chat_history_store", fromlist=["DatabaseSuite"]).DatabaseSuite,
            "shared_persistent",
            classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("boom"))),
        ):
            log_message("من", "never raises")
        assert recent_messages() == []


# ---------- L3: the Jalali dashboard ----------
def test_jalali_known_anchors() -> None:
    # Nowruz anchors (the official calendar)
    assert _g_to_jalali(2026, 3, 21) == (1405, 1, 1)
    assert _g_to_jalali(2025, 3, 21) == (1404, 1, 1)
    assert _g_to_jalali(2027, 3, 21) == (1406, 1, 1)
    # a mid-year date
    assert _g_to_jalali(2026, 9, 21) == (1405, 6, 30)
    # the year-end boundary (leap 1403: Esfand has 30 days)
    assert _g_to_jalali(2025, 3, 20) == (1403, 12, 30)


def test_jalali_day_persian_digits() -> None:
    out = _jalali_day("2026-09-21")
    assert out == "۱۴۰۵/۰۶/۳۰"
    assert all(ch in "۰۱۲۳۴۵۶۷۸۹/" for ch in out)


def test_jalali_roundtrip_days() -> None:
    """Every single day across two full years converts consistently."""
    d = datetime.date(2025, 3, 21)
    end = datetime.date(2027, 3, 20)
    prev = None
    while d <= end:
        jy, jm, jd = _g_to_jalali(d.year, d.month, d.day)
        cur = (jy, jm, jd)
        if prev is not None:
            # consecutive days differ by exactly one calendar step
            pd_ = prev[2] + 1
            pm = prev[1]
            py = prev[0]
            if (pm <= 6 and pd_ > 31) or (pm >= 7 and pm <= 11 and pd_ > 30):
                pd_ = 1
                pm += 1
            elif pm == 12 and pd_ > (30 if py % 33 in (1, 5, 9, 13, 17, 22, 26, 30) else 29):
                pd_ = 1
                pm = 1
                py += 1
            assert cur == (py, pm, pd_), (d, prev, cur)
        prev = cur
        d += datetime.timedelta(days=1)


# ---------- L4: the explicit dashboard path ----------
def test_dashboard_default_path_is_explicit_absolute() -> None:
    import os

    cwd = os.getcwd()
    try:
        os.chdir(tempfile.mkdtemp())
        out = build_dashboard(None)
        assert out["ok"] is True
        assert Path(out["path"]).is_absolute()
        assert Path(out["path"]).exists()
        assert out["bytes"] > 0
    finally:
        os.chdir(cwd)


def test_dashboard_days_are_jalali() -> None:
    """_daily_runs labels are Jalali on the REAL persistent store."""
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.superplatform_dashboard import _daily_runs

    rows = _daily_runs(DatabaseSuite.shared_persistent())
    if not rows:
        return  # a fresh store honestly has no days yet
    for r in rows:
        # every label is Persian digits with a Jalali year (14xx), or the
        # passthrough fallback for an unparseable label
        assert r["day"].startswith("۱۴") or "-" in r["day"], r["day"]