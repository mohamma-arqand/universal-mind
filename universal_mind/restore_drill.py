"""The restore drill — a backup that has never been restored is only hope.

R44 item 15: the platform keeps rotating backups of mind.db, but until a
backup has actually been RESTORED and proven identical to the live store, the
recovery path is an assumption, not a capability. This module runs that drill
against a THROWAWAY COPY — never the operator's live database:

1. Copy the newest backup (or the live store) into a temp directory.
2. Open the copy, run ``PRAGMA integrity_check``.
3. COUNT every table's rows in both the source and the restored copy.
4. Report the comparison honestly: same counts = the drill passed; any
   divergence names the table that diverged.

The drill must be safe to run at any moment (the tick calls it monthly):
it never writes anywhere near the live store.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_LAST_DRILL = ""  # the newest drill's one-line verdict ('' = never run)


def last_drill_verdict() -> str:
    """The last restore drill's verdict ('' = never drilled — honest)."""
    return _LAST_DRILL


@dataclass(frozen=True)
class DrillResult:
    """One restore drill's honest outcome."""

    ok: bool
    source: str
    restored: str
    tables: dict[str, tuple[int, int]]  # table -> (source rows, restored rows)
    integrity: str
    diverged: list[str]
    error: str


def _newest_backup(store_dir: Path) -> Path | None:
    """The newest timestamped backup, or None (the drill names it honestly)."""
    import re

    candidates = [
        p
        for p in store_dir.glob("mind.db.bak-2*")
        if p.is_file() and p.stat().st_size > 0 and not p.name.endswith("-journal")
    ]
    stamp = re.compile(r"^mind\.db\.bak-(\d{8}-\d{6})$")
    dated = [(m.group(1), p) for p in candidates if (m := stamp.match(p.name))]
    if not dated:
        return None
    return max(dated, key=lambda pair: pair[0])[1]


def _row_counts(db_path: Path) -> dict[str, int]:
    """Every user table's real row count (the truth a restore must match)."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        counts: dict[str, int] = {}
        for name in names:
            counts[name] = int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        return counts
    finally:
        conn.close()


def run_restore_drill(store_dir: str | Path | None = None) -> DrillResult:
    """Prove the recovery path on a THROWAWAY copy of the newest backup.

    Never touches the live store: the backup is copied to a temp dir, opened,
    integrity-checked, and compared table-by-table with its source. A backup
    that is missing, unreadable, or divergent is reported BY NAME — the drill
    must never say "healthy" about a path it did not actually walk.
    """
    import shutil
    import sqlite3
    import tempfile

    from universal_mind.database_suite import DatabaseSuite

    root = Path(store_dir) if store_dir else DatabaseSuite.DEFAULT_DB_DIR
    source = _newest_backup(root)
    if source is None:
        return DrillResult(
            ok=False, source="", restored="", tables={}, integrity="",
            diverged=[], error="هیچ بکاپ سالمی برای مانور نیست — اول backup_database را اجرا کن.",
        )

    scratch = Path(tempfile.mkdtemp(prefix="um-drill-"))
    restored = scratch / "restored.db"
    try:
        shutil.copy2(source, restored)
    except OSError as exc:
        return DrillResult(
            ok=False, source=str(source), restored="", tables={}, integrity="",
            diverged=[], error=f"کپی بکاپ شکست خورد: {exc}",
        )

    # 1. the copy OPENS and passes integrity
    try:
        conn = sqlite3.connect(str(restored))
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        conn.close()
    except sqlite3.Error as exc:
        return DrillResult(
            ok=False, source=str(source), restored=str(restored), tables={},
            integrity="failed", diverged=[], error=f"بکاپ باز نمیشود: {exc}",
        )
    if integrity != "ok":
        return DrillResult(
            ok=False, source=str(source), restored=str(restored), tables={},
            integrity=integrity, diverged=[],
            error=f"بکاپ سالم نیست (integrity_check: {integrity}).",
        )

    # 2. every table's row count matches the source
    try:
        src_counts = _row_counts(source)
        new_counts = _row_counts(restored)
    except sqlite3.Error as exc:
        return DrillResult(
            ok=False, source=str(source), restored=str(restored), tables={},
            integrity=integrity, diverged=[], error=f"شمارش سطرها شکست خورد: {exc}",
        )
    tables: dict[str, tuple[int, int]] = {}
    diverged: list[str] = []
    for name in sorted(set(src_counts) | set(new_counts)):
        a, b = src_counts.get(name, -1), new_counts.get(name, -1)
        tables[name] = (a, b)
        if a != b:
            diverged.append(name)

    ok = not diverged
    error = "" if ok else f"این جدولها بعد از بازیابی واگرا شدند: {diverged}"
    # R46-15 — the drill's verdict is a FACT that sticks (the backup-health
    # answer reads it): a drill that ran is never again "never drilled".
    global _LAST_DRILL
    _fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    n_tables = str(len(tables)).translate(_fa)
    _LAST_DRILL = (
        f"مانورِ آخر: بازیابی {'موفق' if ok else 'ناموفق'} — {n_tables} جدول، "
        f"integrity: {integrity}"
        + (f" | واگرا: {diverged[:3]}" if diverged else "")
    )
    return DrillResult(
        ok=ok, source=str(source), restored=str(restored),
        tables=tables, integrity=integrity, diverged=diverged, error=error,
    )


