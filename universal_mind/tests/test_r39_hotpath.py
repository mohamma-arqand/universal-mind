"""Tests: R39 — hot-path durability. The persistent file is validated once
per process; explicit-path suites validate EVERY time (corruption never
sneaks past); the shared suite is one wrapper, one file.
"""

from __future__ import annotations

import pytest

import tempfile
from pathlib import Path

from universal_mind.database_suite import DatabaseSuite


def test_corrupt_explicit_path_still_fails_early() -> None:
    """A corrupted file at an EXPLICIT path must fail loudly, every time."""
    d = Path(tempfile.mkdtemp()) / "corrupt.db"
    d.write_bytes(b"NOT-SQLITE-HEADER!" + b"\x00" * 48)
    try:
        DatabaseSuite(str(d))
        raise AssertionError("corruption must not pass")
    except RuntimeError as e:
        assert "خراب" in str(e)


@pytest.mark.live_store  # type: ignore[untyped-decorator]


def test_shared_persistent_is_one_wrapper() -> None:
    a = DatabaseSuite.shared_persistent()
    b = DatabaseSuite.shared_persistent()
    assert a is b
    assert Path(a.db_path) == Path.home() / ".universal-mind" / "mind.db"


@pytest.mark.live_store  # type: ignore[untyped-decorator]


def test_shared_persistent_writes_and_reads() -> None:
    suite = DatabaseSuite.shared_persistent()
    suite.execute(
        "CREATE TABLE IF NOT EXISTS r39_probe (v TEXT)"
    )
    suite.execute("DELETE FROM r39_probe")
    suite.insert_many("r39_probe", [{"v": "alive"}])
    q = suite.query("SELECT COUNT(*) AS n FROM r39_probe")
    assert q["ok"] and q["rows"][0]["n"] == 1
    suite.execute("DROP TABLE r39_probe")


def test_explicit_temp_suite_unaffected() -> None:
    """A fresh temp suite (the throwaway default) still works as before."""
    suite = DatabaseSuite()
    assert suite.execute("CREATE TABLE t (v TEXT)")["ok"] is True
