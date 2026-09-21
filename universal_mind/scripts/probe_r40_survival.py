#!/usr/bin/env python3
"""Probe: R40 — the surviving conversation, the clickable fix, the Jalali
dashboard (verified against jdatetime when present), and the explicit
dashboard path. All live in the release gate."""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R40 survival:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    from universal_mind.chat_history_store import log_message, message_count, recent_messages
    from universal_mind.superplatform_dashboard import _g_to_jalali, build_dashboard

    # L1 — the conversation survives: log and read back.
    before = message_count()
    log_message("probe", "پیام آزمایشی R40")
    msgs = recent_messages(limit=5)
    _ok("chat survives", message_count() == before + 1 and msgs[-1]["who"] == "probe")

    # L3 — the Jalali conversion: known anchors + (if jdatetime exists) a
    # multi-year exhaustive diff.
    _ok("jalali nowruz 1405", _g_to_jalali(2026, 3, 21) == (1405, 1, 1))
    _ok("jalali mid-year", _g_to_jalali(2026, 9, 21) == (1405, 6, 30))
    _ok("jalali leap esfand", _g_to_jalali(2025, 3, 20) == (1403, 12, 30))
    try:
        import datetime
        import jdatetime

        d = datetime.date(2025, 1, 1)
        bad = 0
        while d <= datetime.date(2028, 12, 31):
            j = jdatetime.date.fromgregorian(date=d)
            if (j.year, j.month, j.day) != _g_to_jalali(d.year, d.month, d.day):
                bad += 1
            d += datetime.timedelta(days=1)
        _ok("jalali vs jdatetime 4yr", bad == 0, f"bad={bad}")
    except ImportError:
        _ok("jalali vs jdatetime 4yr", True, "jdatetime absent — anchors only")

    # L4 — the explicit absolute dashboard path with Jalali days inside.
    import tempfile
    from pathlib import Path

    out = build_dashboard(str(Path(tempfile.mkdtemp()) / "probe-dash.html"))
    _ok("dashboard renders", bool(out.get("ok")) and out.get("bytes", 0) > 0,
        f"{out.get('bytes')} bytes")
    html = Path(str(out.get("path"))).read_text(encoding="utf-8")
    _ok("dashboard jalali days", "۱۴۰" in html or "۱۴۰۵" in html or "۱۴۰۴" in html)

    # L2 — the chip factory: the desktop app carries the suggestion chips.
    from universal_mind import desktop_app as da

    _ok("chips wired", hasattr(da.MindDesktopApp, "_show_suggestion_chips"))

    sys.stderr.write("R40 survival: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())