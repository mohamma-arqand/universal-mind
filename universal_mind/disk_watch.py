"""The disk watch — the 60GB lesson, never again learned twice.

R45 item 14: the scratch reaper once filled a whole disk (124k dirs /
~60GB) before anyone noticed. The tick now reads the store drive's REAL
free space every run and raises a toast the moment it drops below the
floor (default 20GB — enough for a month of backups and a restore drill).
The reading is shutil.disk_usage on the STORE directory's drive, not an
estimate; a read failure says so honestly instead of reporting a green
zero.
"""

from __future__ import annotations

import shutil
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

DEFAULT_FLOOR_GB = 20.0


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def disk_report(*, floor_gb: float = DEFAULT_FLOOR_GB) -> dict[str, Any]:
    """The real free space on the store's drive vs the floor."""
    try:
        drive = str(DatabaseSuite.DEFAULT_DB_DIR)
        usage = shutil.disk_usage(drive)
        free_gb = usage.free / (1024 ** 3)
        ok = free_gb >= floor_gb
        return {
            "ok": ok,
            "free_gb": round(free_gb, 1),
            "floor_gb": floor_gb,
            "drive": drive,
            "report": (
                f"فضای آزاد درایو {_fa(round(free_gb, 1))} گیگابایت "
                + ("— سلامت است." if ok else f"— از کفِ {_fa(floor_gb)} گیگابایت پایینتر است!")
            ),
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 — a failed gauge says so
        return {"ok": False, "free_gb": 0.0, "floor_gb": floor_gb, "drive": "?",
                "report": f"فضای دیسک خوانده نشد: {exc}", "error": str(exc)}
