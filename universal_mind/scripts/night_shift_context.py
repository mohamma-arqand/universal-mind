#!/usr/bin/env python3
"""THE NIGHT-SHIFT GUARD — the context + lock a scheduled run needs.

Run once per cron tick. It:

* holds a LOCK so two runs never touch ``mind.db`` at once (35-min cadence,
  25-min staleness — a hung run never blocks the night);
* prints the CURRENT state of the shift as plain text (manifest cursor, open
  git state, last commits, the tail of the shift log) so the agent's prompt
  arrives with real context instead of guesses;
* appends one heartbeat line to ``docs/NIGHT_SHIFT_LOG.md`` per STARTED run —
  the operator wakes up to a timeline, not a claim.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_UM = _REPO / "universal_mind"
_MANIFEST = _UM / "docs" / "NIGHT_SHIFT.md"
_LOG = _UM / "docs" / "NIGHT_SHIFT_LOG.md"
_LOCK = _UM / "docs" / ".night_shift.lock"
_STALE_SECONDS = 25 * 60


def _run(*args: str) -> str:
    try:
        out = subprocess.run(
            args, cwd=str(_REPO), capture_output=True, text=True, timeout=60,
        )
        return (out.stdout or out.stderr or "").strip()
    except Exception as exc:  # never let context-gathering kill the tick
        return f"(could not run {' '.join(args)}: {exc})"


def _lock_state() -> tuple[str, bool]:
    """Return (message, may_proceed).

    The lock is taken ATOMICALLY (``O_CREAT|O_EXCL``): a plain
    ``exists()``-then-``write`` is a TOCTOU race, and a real night proved it —
    two runs both read "no lock" and both proceeded, editing the same files.
    Creation-or-refusal in one syscall is the only version that holds.
    """
    fresh = False
    if _LOCK.exists():
        age = time.time() - _LOCK.stat().st_mtime
        if age < _STALE_SECONDS:
            return (
                f"LOCK: LIVE — a run started {int(age // 60)} min ago is still "
                "working. DO NOTHING this tick: no edits, no commits, no tests.",
                False,
            )
        # STALE: O_EXCL alone can never take an existing file, so the dead
        # lock must be REMOVED first. Two runs may both unlink (one gets
        # FileNotFoundError, ignored); the create below then decides the
        # winner — the race is settled in one atomic syscall, not by trust.
        try:
            _LOCK.unlink()
        except FileNotFoundError:
            pass
        fresh = True

    try:
        fd = os.open(str(_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # somebody created it between our check and our create — they won
        age = time.time() - _LOCK.stat().st_mtime
        if age < _STALE_SECONDS:
            return (
                "LOCK: LIVE — another run won the atomic create; it is "
                "working. DO NOTHING this tick.",
                False,
            )
        return (
            "LOCK: a stale lock could not be taken atomically (race) — "
            "DO NOTHING this tick; the next tick will retry.",
            False,
        )
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{time.time():.3f}\n")
    return (
        f"LOCK: {'replaced a stale lock — ' if fresh else ''}acquired atomically — proceed.",
        True,
    )




def _cursor_lines() -> str:
    if not _MANIFEST.exists():
        return "(manifest missing — create it before working)"
    lines = _MANIFEST.read_text(encoding="utf-8").splitlines()
    keep: list[str] = []
    for i, line in enumerate(lines):
        if "آیتم بعدی" in line or "آخرین ران" in line:
            keep.append(line.strip())
        if line.startswith("| N") and "⬜" in line:
            keep.append(line.strip())
    return "\n".join(keep) if keep else "(no open items in the manifest table)"


def _open_items() -> int:
    if not _MANIFEST.exists():
        return -1
    return sum(
        1 for ln in _MANIFEST.read_text(encoding="utf-8").splitlines()
        if ln.startswith("| N") and "⬜" in ln
    )


def main() -> int:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg, may = _lock_state()

    print("=== NIGHT SHIFT STATE ===")
    print(f"now: {stamp}")
    print(msg)
    print(f"open items remaining: {_open_items()}")
    print()
    print("--- manifest cursor ---")
    print(_cursor_lines())
    print()
    print("--- last commits ---")
    print(_run("git", "log", "--oneline", "-4"))
    print()
    print("--- working tree ---")
    print(_run("git", "status", "--short") or "(clean)")
    print()
    print("--- shift log tail ---")
    if _LOG.exists():
        tail = _LOG.read_text(encoding="utf-8").splitlines()[-8:]
        print("\n".join(tail) if tail else "(empty)")
    else:
        print("(no log yet)")
    print()

    if may:
        # heartbeat: proof-of-life for the operator, one line per STARTED run
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"- [{stamp}] run started (lock acquired)\n")
        print("PROCEED: do the next manifest item, then release the lock:")
        print(f"  rm -f {_LOCK}")
    else:
        print("STOP: another run is live. Make no changes and end your turn.")

    # release the lock if the run found nothing to do
    if not _MANIFEST.exists() or _open_items() == 0:
        pass  # the agent decides (it may generate the next wave)
    return 0


if __name__ == "__main__":
    sys.exit(main())
