"""A shared cleanup fixture: tests must never pollute the operator's store.

Every test file that touches the PERSISTENT store (history/lessons/goals)
imports this module's autouse fixture: any row whose command/goal carries a
TEST marker (the prefixes this platform's own tests use) is removed after
the suite — the live store belongs to the OPERATOR, not the test run.
"""

from __future__ import annotations

import pytest


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
