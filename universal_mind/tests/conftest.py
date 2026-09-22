"""A shared cleanup fixture: tests must never pollute the operator's store.

Every test file that touches the PERSISTENT store (history/lessons/goals)
imports this module's autouse fixture: any row whose command/goal carries a
TEST marker (the prefixes this platform's own tests use) is removed after
the suite — the live store belongs to the OPERATOR, not the test run.
"""

from __future__ import annotations

from typing import Iterator

import pytest


def pytest_configure(config: object) -> None:
    """Register the live_store marker (tests that read the operator's store)."""
    getattr(config, "addinivalue_line")(
        "markers", "live_store: this test reads the operator's REAL store."
    )


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _isolated_shared_store(request: object) -> Iterator[object]:
    """Every test reads/writes an ISOLATED store — never the operator's.

    shared_persistent is re-pointed to a fresh temp suite for the duration
    of each test (R42), UNLESS the test carries the `live_store` marker —
    the explicit opt-in for the handful of tests whose whole point is the
    operator's real recorded history.
    """
    node = getattr(request, "node", None)
    if node is not None and any(m.name == "live_store" for m in node.iter_markers()):
        yield None  # the test explicitly wants the operator's real store
        return
    import tempfile
    from contextlib import ExitStack
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    with ExitStack() as stack:
        suite = DatabaseSuite(str(Path(tempfile.mkdtemp(prefix="um-test-")) / "test.db"))
        stack.enter_context(
            mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: suite))
        )
        yield suite



@pytest.fixture(autouse=True, scope="session")  # type: ignore[untyped-decorator]
def _purge_test_rows_after_suite() -> object:
    """After the whole session: remove obvious test rows from the live store.

    Only rows with unmistakable test markers are touched (the 68-schedule
    lesson: even so, tests should write to isolated stores; this is the
    safety NET, not the license).
    """
    yield
    try:
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite(persistent=True)
        # test commands carry latin hex tails or explicit markers
        db.execute(
            "DELETE FROM schedules WHERE command LIKE '%میانگین 1 و 2%' "
            "OR command LIKE '%میانگین 3 و 7%' "
            "OR command LIKE '%میانگین 5 و 9%'"
        )
        db.execute(
            "DELETE FROM goals WHERE goal LIKE '%آزمون%' OR goal LIKE '%هدف: آزمون%'"
        )
    except Exception:  # noqa: BLE001 — cleanup never fails a suite
        pass
