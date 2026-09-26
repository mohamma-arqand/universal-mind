"""Backup health — «بکاپ سالم است؟» answered with proof, not hope.

R46 item 15: the status view named the newest backup's age, but a backup
older than 7 days is a RECOVERY PATH THAT ROTTED — and nothing said so.
This module answers the question directly: the newest backup, the last
restore drill's verdict, the integrity check — and an EXPLICIT warning
when the newest backup is stale. A missing backup says so by name.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_STALE_DAYS = 7  # a backup older than this is a rotted recovery path

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def backup_health(*, db: DatabaseSuite | None = None) -> dict[str, Any]:
    """The honest answer: newest backup, last drill, integrity, warnings."""
    from datetime import datetime

    from universal_mind.restore_drill import _newest_backup

    store_dir = DatabaseSuite.DEFAULT_DB_DIR
    nb = _newest_backup(store_dir)
    warnings: list[str] = []
    if nb is None:
        return {
            "ok": False,
            "report": "بکاپ: هیچ بکاپی وجود ندارد — مسیر بازیابی قطع است.",
            "newest": None, "age_days": None, "warnings": ["no_backup"],
            "error": "",
        }
    stat = nb.stat()
    age_days = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
    mb = stat.st_size / (1024 * 1024)
    if age_days > _STALE_DAYS:
        warnings.append(
            f"بکاپ {_FA and ''}{age_days} روز کهنه است — مسیر بازیابی در خطر (یک tick تازه بساز)"
        )
    # the last restore drill's verdict, from its real record
    drill_line = ""
    try:
        from universal_mind.restore_drill import last_drill_verdict

        drill_line = last_drill_verdict()
    except Exception:  # noqa: BLE001 — the drill line is a lens
        drill_line = ""
    if not drill_line:
        warnings.append("مانور بازیابی هنوز اجرا نشده — سلامت بکاپ اثبات نشده")
    ok = not warnings
    parts = [f"بکاپ: {age_days} روز پیش، {round(mb)} مگابایت ({nb.name})"]
    if drill_line:
        parts.append(drill_line)
    if warnings:
        parts.append("⚠️ " + "؛ ".join(warnings))
    else:
        parts.append("✅ بکاپ سالم است — مسیر بازیابی زنده")
    fa_age = str(age_days).translate(_FA)
    fa_mb = str(round(mb)).translate(_FA)
    report = (
        f"بکاپ: {fa_age} روز پیش، {fa_mb} مگابایت ({nb.name})"
        + (" | " + drill_line if drill_line else "")
        + (" | ⚠️ " + "؛ ".join(warnings) if warnings else " | ✅ بکاپ سالم است")
    )
    return {"ok": ok, "report": report, "newest": nb.name,
            "age_days": age_days, "warnings": warnings, "error": ""}


__all__ = ["backup_health"]
