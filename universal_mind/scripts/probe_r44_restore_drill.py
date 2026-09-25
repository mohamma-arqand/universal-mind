#!/usr/bin/env python3
"""Probe: R44 item 15 — the restore drill (live, on the REAL newest backup).

A backup that has never been restored is only hope. This probe walks the
actual recovery path end to end: the operator's newest timestamped backup is
copied to a throwaway dir, opened, integrity-checked, and compared
table-by-table with its source. Plus the failure laws: no backup = a named
refusal; a corrupt backup = caught; the drill never touches the live store.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-15 (the restore drill):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import tempfile

    from universal_mind.restore_drill import run_restore_drill

    # H1 — the LIVE drill on the operator's real newest backup.
    drill = run_restore_drill()
    _ok("the real newest backup restores clean", drill.ok,
        drill.error or f"{len(drill.tables)} tables, integrity {drill.integrity}")
    _ok("integrity_check says ok", drill.integrity == "ok")
    _ok("row counts really match", not drill.diverged,
        f"diverged={drill.diverged}")

    # H2 — the honest refusals.
    empty = Path(tempfile.mkdtemp())
    bare = run_restore_drill(empty)
    _ok("no backup is a named refusal", bare.ok is False and "بکاپ" in bare.error)

    bad_dir = Path(tempfile.mkdtemp())
    (bad_dir / "mind.db.bak-20260101-090000").write_bytes(b"NOT-SQLITE!" + b"\x00" * 48)
    corrupt: Any = run_restore_drill(bad_dir)
    _ok("a corrupt backup is caught", corrupt.ok is False)

    # H3 — the drill never writes near the live store.
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        conn = sqlite3.connect(str(store / "mind.db.bak-20260101-090000"))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        src = store / "mind.db.bak-20260101-090000"
        before = src.stat().st_mtime_ns
        r = run_restore_drill(store)
        _ok("the source file is untouched", src.stat().st_mtime_ns == before and r.ok)

    sys.stderr.write("R44-15: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
