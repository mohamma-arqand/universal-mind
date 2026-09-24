"""Tests: R44 — scratch hygiene (the leak that filled the disk).

Live incident: one 16-minute suite left 124,000 ``um-db-*`` directories and
tens of GB in the system temp dir, and a failing backup accumulated junk
exactly when space was scarcest. Both leaks are closed; these laws keep them.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch


def _make_scratch(root: Path, name: str, age_s: float) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "mind.db").write_bytes(b"x" * 64)
    old = time.time() - age_s
    os.utime(d, (old, old))
    return d


class TestScratchReaper:
    """Stale scratch goes; young scratch (possibly live) stays."""

    def test_old_scratch_is_reaped_and_young_is_kept(self, tmp_path: Path) -> None:
        import universal_mind.database_suite as ds

        stale = _make_scratch(tmp_path, "um-db-stale", age_s=7200)
        live = _make_scratch(tmp_path, "um-db-live", age_s=5)
        other = _make_scratch(tmp_path, "um-chart-stale", age_s=7200)
        not_ours = _make_scratch(tmp_path, "unrelated-dir", age_s=7200)

        with mock_patch("tempfile.gettempdir", lambda: str(tmp_path)):
            removed = ds.reap_stale_scratch(force=True)  # bypass the throttle

        assert removed == 2, f"expected the two stale um-* dirs, got {removed}"
        assert not stale.exists()
        assert not other.exists()
        assert live.exists(), "a young scratch dir may belong to a live suite"
        assert not_ours.exists(), "only the platform's own prefixes are reaped"

    def test_the_sweep_is_throttled(self, tmp_path: Path) -> None:
        import universal_mind.database_suite as ds

        _make_scratch(tmp_path, "um-db-old", age_s=7200)
        with mock_patch("tempfile.gettempdir", lambda: str(tmp_path)):
            first = ds.reap_stale_scratch(force=True)
            second = ds.reap_stale_scratch()  # same instant: must be a no-op
        assert first == 1
        assert second == 0, "the sweep must not walk the temp dir on every call"

    def test_a_scratch_suite_sweeps_but_an_explicit_path_does_not(
        self, tmp_path: Path
    ) -> None:
        """The real wiring: building a SCRATCH suite is what reaps."""
        import universal_mind.database_suite as ds

        _make_scratch(tmp_path, "um-db-ancient", age_s=7200)
        # throttle armed at "now": a sweep would be skipped if it were called
        with mock_patch("tempfile.gettempdir", lambda: str(tmp_path)), \
             mock_patch.object(ds, "_last_reap", time.time()):
            ds.DatabaseSuite(str(tmp_path / "explicit.db"))  # explicit: no sweep
        assert (tmp_path / "um-db-ancient").exists(), "explicit paths must not sweep"

        with mock_patch("tempfile.gettempdir", lambda: str(tmp_path)), \
             mock_patch.object(ds, "_last_reap", 0.0):  # throttle open
            ds.DatabaseSuite()  # scratch: this is the sweep trigger
        assert not (tmp_path / "um-db-ancient").exists()


class TestBackupPruneOnFailure:
    """A failed backup must not become permanent junk."""

    def _fake_store(self, tmp_path: Path, count: int) -> Path:
        for i in range(count):
            (tmp_path / f"mind.db.bak-2026010{i}-000000").write_bytes(b"old")
        conn = sqlite3.connect(str(tmp_path / "mind.db"))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        return tmp_path

    def test_a_full_disk_leaves_no_junk(self, tmp_path: Path) -> None:
        from universal_mind import scheduler
        from universal_mind.database_suite import DatabaseSuite

        store = self._fake_store(tmp_path, 5)
        with mock_patch.object(DatabaseSuite, "DEFAULT_DB_DIR", store), \
             mock_patch("sqlite3.connect", side_effect=OSError("No space left on device")):
            res: Any = scheduler.backup_database(keep=2)
        assert res["ok"] is False and "No space" in res["error"]
        # prune ran even though the copy failed: no unbounded pile of backups
        left = sorted(p.name for p in store.glob("mind.db.bak-2*"))
        assert len(left) == 2, left

    def test_a_successful_backup_keeps_only_the_window(self, tmp_path: Path) -> None:
        from universal_mind import scheduler
        from universal_mind.database_suite import DatabaseSuite

        store = self._fake_store(tmp_path, 5)
        with mock_patch.object(DatabaseSuite, "DEFAULT_DB_DIR", store):
            res: Any = scheduler.backup_database(keep=2)
        assert res["ok"] is True, res
        left = sorted(p.name for p in store.glob("mind.db.bak-2*"))
        assert len(left) <= 3, left  # the window, plus the newest copy
        # the created backup is a readable database, not a truncated file
        probe = sqlite3.connect(res["backup"])
        assert probe.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        probe.close()
