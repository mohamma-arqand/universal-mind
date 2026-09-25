"""Tests: R44 item 15 — the restore drill (a backup proven, not hoped).

Live laws:
1. A real backup restores: copy opens, integrity ok, every table's row
   count matches — and the drill names every table it compared.
2. No backup = an honest named refusal, never a silent pass.
3. A CORRUPT backup is caught: the drill says unhealthy by name.
4. A TRUNCATED backup (a zero-byte or garbage file) is never picked.
5. The drill never touches the live store — its writes stay in temp.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _make_store(tmp_path: Path, rows: int = 3) -> Path:
    """A real backup file with one table, `rows` rows, named like the rotation."""
    db_path = tmp_path / "mind.db.bak-20260101-090000"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE run_history (id INTEGER PRIMARY KEY, x INTEGER)")
    for i in range(rows):
        conn.execute("INSERT INTO run_history (x) VALUES (?)", (i,))
    conn.commit()
    conn.close()
    return db_path


class TestTheDrill:
    def test_a_real_backup_restores_clean(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        _make_store(tmp_path, rows=5)
        r = run_restore_drill(tmp_path)
        assert r.ok is True, r.error
        assert r.integrity == "ok"
        assert r.tables == {"run_history": (5, 5)}
        assert r.diverged == []

    def test_the_drill_never_writes_inside_the_store(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        src = _make_store(tmp_path, rows=2)
        before = src.stat().st_mtime_ns
        run_restore_drill(tmp_path)
        assert src.stat().st_mtime_ns == before, "the drill must not touch the source"
        assert not (tmp_path / "restored.db").exists(), "the copy stays in temp"

    def test_no_backup_is_an_honest_refusal(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        r = run_restore_drill(tmp_path)
        assert r.ok is False
        assert "بکاپ" in r.error

    def test_a_corrupt_backup_is_caught_by_name(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        bad = tmp_path / "mind.db.bak-20260102-090000"
        bad.write_bytes(b"NOT-SQLITE-HEADER!" + b"\x00" * 48)
        r = run_restore_drill(tmp_path)
        assert r.ok is False
        assert r.integrity != "ok" or "باز نمیشود" in r.error

    def test_junk_and_journal_files_are_never_picked(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        (tmp_path / "mind.db.bak-20260103-090000-journal").write_bytes(b"x" * 512)
        (tmp_path / "mind.db.bak-20260104-090000").write_bytes(b"")  # zero bytes
        r = run_restore_drill(tmp_path)
        assert r.ok is False and "بکاپ" in r.error

    def test_the_newest_backup_wins(self, tmp_path: Path) -> None:
        from universal_mind.restore_drill import run_restore_drill

        _make_store(tmp_path, rows=1)  # older date 20260101
        # build the newer one in its own subdir, then move it in with the newer name
        own = tmp_path / "own"
        own.mkdir()
        newer = _make_store(own, rows=9)
        newer.rename(tmp_path / "mind.db.bak-20260601-090000")
        (own).rmdir()
        r = run_restore_drill(tmp_path)
        assert r.ok is True
        assert r.tables == {"run_history": (9, 9)}, r.tables
