"""Tests: WAL journal mode + verified backups (the durability layer)."""

from __future__ import annotations

from pathlib import Path


class TestWALMode:
    def test_a_new_persistent_connection_switches_to_wal(self, tmp_path: Path) -> None:
        """Opening the persistent store flips it to WAL (concurrency-safe)."""
        import sqlite3

        from universal_mind.database_suite import DatabaseSuite

        db_path = tmp_path / "mind.db"
        db_path.write_bytes(b"")  # an empty file: the header guard skips it
        suite = DatabaseSuite(db_path=str(db_path))
        suite.execute("CREATE TABLE IF NOT EXISTS t (x TEXT)")
        mode = sqlite3.connect(str(db_path)).execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_the_live_store_is_wal_after_use(self) -> None:
        """The REAL persistent store runs in WAL (this is a live-system check)."""
        import sqlite3

        from universal_mind.database_suite import DatabaseSuite

        DatabaseSuite(persistent=True).tables()  # open it (flips WAL)
        mode = sqlite3.connect(
            str(DatabaseSuite.DEFAULT_DB_DIR / "mind.db")
        ).execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


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
