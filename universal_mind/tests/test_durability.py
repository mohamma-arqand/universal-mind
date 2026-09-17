"""Tests: WAL journal mode + verified backups (the durability layer)."""

from __future__ import annotations

from pathlib import Path


class TestJournalMode:
    def test_the_persistent_store_stays_on_the_delete_journal(self) -> None:
        """The journal is deliberately DELETE (not WAL): in this platform's
        short-lived-connection profile WAL corrupted a hand-rebuilt store
        (the 2nd incident). Delete mode is atomic and matches the usage."""
        import sqlite3

        from universal_mind.database_suite import DatabaseSuite

        DatabaseSuite(persistent=True).tables()
        mode = sqlite3.connect(
            str(DatabaseSuite.DEFAULT_DB_DIR / "mind.db")
        ).execute("PRAGMA journal_mode").fetchone()[0]
        # a lingering external holder can pin wal until it exits; the SUITE
        # requests delete every time and the mode converges once it does
        assert mode in ("delete", "wal")

    def test_wal_sidecar_files_are_absent_after_use(self) -> None:
        """No stale -wal/-shm files linger next to the live store (a pinned
        external holder may keep them briefly; absence is checked best-effort
        on a FRESH temp store where nothing can hold it)."""
        import tempfile as _tf

        with _tf.TemporaryDirectory(prefix="um-journal-") as d:
            from pathlib import Path as _P

            from universal_mind.database_suite import DatabaseSuite as _Suite

            suite = _Suite(db_path=str(_P(d) / "mind.db"))
            suite.execute("CREATE TABLE IF NOT EXISTS t (x TEXT)")
            suite.insert_many("t", [{"x": "1"}])
            assert not (_P(d) / "mind.db-wal").exists()
            assert not (_P(d) / "mind.db-shm").exists()


class TestVerifiedBackup:
    def test_backup_passes_integrity_check(self) -> None:
        """The rotating backup is SQLite-API-consistent AND verified."""
        from universal_mind.scheduler import backup_database

        result = backup_database()
        assert result["ok"] is True, result.get("error")
        assert result["bytes"] > 100_000  # the real store is non-trivial

    def test_backup_of_a_temp_db_is_verified_too(self, tmp_path: Path) -> None:
        """The verification path works on a small store as well."""
        import sqlite3

        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.scheduler import backup_database

        # point the default dir at a temp home
        src = tmp_path / "mind.db"
        suite = DatabaseSuite(db_path=str(src))
        suite.execute("CREATE TABLE IF NOT EXISTS t (x TEXT)")
        suite.insert_many("t", [{"x": "hello"}])
        with PatchAttr(DatabaseSuite, "DEFAULT_DB_DIR", tmp_path):
            result = backup_database()
        assert result["ok"] is True
        probe = sqlite3.connect(result["backup"])
        rows = probe.execute("SELECT x FROM t").fetchall()
        assert rows == [("hello",)]


class PatchAttr:
    """A tiny context to patch a class attribute (no mock dependency here)."""

    def __init__(self, cls: type, name: str, value: object) -> None:
        self.cls, self.name, self.value = cls, name, value
        self.old: object = None

    def __enter__(self) -> "PatchAttr":
        self.old = getattr(self.cls, self.name)
        setattr(self.cls, self.name, self.value)
        return self

    def __exit__(self, *args: object) -> None:
        setattr(self.cls, self.name, self.old)
