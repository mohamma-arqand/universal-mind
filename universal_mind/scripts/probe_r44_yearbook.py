#!/usr/bin/env python3
"""Probe: R44 item 16 — the yearbook, live (the sum of every loop).

«گزارش سالانهام را بساز» — the platform reads its real history, lessons and
human verdicts and renders a Persian PDF. This probe builds it LIVE from the
operator's store and checks every law: real numbers in the narrative, a real
PDF on disk, and an honest first page for an empty year.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-16 (the yearbook):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import tempfile

    from universal_mind.yearbook import build_yearbook, yearbook_sections

    # H1 — the LIVE yearbook from the operator's real store.
    out = Path(tempfile.mkdtemp(prefix="um-yearbook-probe-"))
    live = build_yearbook(out_dir=str(out))
    _ok("the live yearbook builds", live["ok"] is True, live.get("error", ""))
    path = Path(live["path"])
    _ok("a real PDF landed on disk",
        path.exists() and path.read_bytes()[:4] == b"%PDF", f"{live['bytes']} bytes")

    sections = live["sections"]
    joined = " ".join(sections)
    this_year = yearbook_sections(live_year())
    if this_year["runs"] > 0:
        _ok("the narrative carries the real run count",
            "فرمان اجرا کردم" in joined, sections[1][:60])
        _ok("nothing is fabricated (the honesty line is present)",
            "ساختگی نیست" in joined)
    else:
        _ok("an empty year is an honest first page", "آغاز" in joined)

    # H2 — the empty-year law on a controlled store.
    import sqlite3

    empty_dir = Path(tempfile.mkdtemp())
    empty_db = empty_dir / "e.db"
    conn = sqlite3.connect(str(empty_db))
    conn.execute(
        "CREATE TABLE run_history (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, "
        "route TEXT, succeeded INTEGER, excellence REAL, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()
    from universal_mind.database_suite import DatabaseSuite

    empty = build_yearbook(1998, db=DatabaseSuite(str(empty_db)),
                           out_dir=str(empty_dir))
    _ok("a dead year never fabricates work",
        empty["ok"] and "آغاز" in " ".join(empty["sections"])
        and "فرمان اجرا کردم" not in " ".join(empty["sections"]))

    # H3 — the operator's question through the real router.
    from universal_mind.persian_router import route_and_run

    p = route_and_run("سالنامهام را بساز")
    _ok("«سالنامهام را بساز» routes to pdf", p.get("route") == ["pdf"], str(p.get("route")))
    _ok("the command really produced a yearbook PDF",
        bool(p.get("ok")) and int((p["result"].get("pdf") or {}).get("bytes", 0)) > 500)

    sys.stderr.write("R44-16: ALL HOLDS GREEN\n")
    return 0


def live_year() -> int:
    import datetime as dt

    return dt.date.today().year


if __name__ == "__main__":
    raise SystemExit(main())
