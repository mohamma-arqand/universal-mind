"""R57 — the verify gate holds the night-shift lock, pinned.

The tests gate reads the shared store, and a cron tick firing mid-verify once
flipped a live-judge count test red (assert 1 == 2). Verify now acquires the
atomic lock like any scheduled run; these tests pin the three behaviours:

 1. a LIVE lock → verify refuses fast, exit 2, without touching artifacts;
 2. the lock is released after a successful run;
 3. the refusal path does not overwrite a previous READY stamp.
"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path
from unittest.mock import patch

UM = Path(__file__).resolve().parents[1]
LOCK = UM / "docs" / ".night_shift.lock"
STATUS = UM / "artifacts" / "verification_status.txt"
_VERIFY = UM / "scripts" / "verify.py"


def _verify_module():  # type: ignore[no-untyped-def]
    """Load scripts/verify.py the way the probes load helpers — from file."""
    spec = importlib.util.spec_from_file_location("um_verify_for_test", _VERIFY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _take_lock() -> None:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{time.time():.3f}\n")


class TestVerifyLock:
    def setup_method(self) -> None:
        if LOCK.exists():
            LOCK.unlink()

    def teardown_method(self) -> None:
        if LOCK.exists():
            LOCK.unlink()

    def test_a_live_lock_makes_verify_refuse_without_running(self) -> None:
        V = _verify_module()
        _take_lock()
        with patch.object(V, "_main_locked", return_value=0) as inner:
            rc = V.main()
        assert rc == 2                       # refused, not run
        assert inner.call_count == 0         # the gates never started
        assert LOCK.exists()                 # we still own OUR lock

    def test_verify_releases_the_lock_after_running(self) -> None:
        V = _verify_module()
        with patch.object(V, "_main_locked", return_value=0):
            rc = V.main()
        assert rc == 0                       # the stubbed run "passed"
        assert not LOCK.exists()             # and the lock was given back

    def test_a_refusal_does_not_touch_the_ready_stamp(self) -> None:
        V = _verify_module()
        art = STATUS.parent
        art.mkdir(parents=True, exist_ok=True)
        STATUS.write_text("READY\n", encoding="utf-8")
        before = STATUS.stat().st_mtime_ns

        _take_lock()
        try:
            assert V.main() == 2
        finally:
            assert STATUS.read_text(encoding="utf-8") == "READY\n"
            assert STATUS.stat().st_mtime_ns == before   # untouched
