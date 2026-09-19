"""Seed memory — the prevention layer BEFORE a capability runs empty.

«بلند بخوان» alone is honest but mute: nothing in the sentence says WHAT
to read aloud, and the speech capability correctly refuses 'empty text'.
But the operator just made things — the platform's own history knows them.

This module reads the last REAL, judged-successful run (chain_results /
run_history) and offers the last run's Persian report as the seed material
for capabilities that would otherwise run empty:

  - speech  «بلند بخوان»      → the last successful run's Persian report
  - clipboard «کپی کن/بگذار»  → the same (the flow layer fills the text)

The seed is a SUGGESTION with provenance: {text, source, proven}. The
params layer only takes it when the sentence itself carries no material
(explicit intent always wins). If there is nothing real to say, the seed
is None — and the honest 'empty text' refusal stays (never fake material).
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite


def last_spoken_material() -> dict[str, Any] | None:
    """The last successful run's report — real, judged, speakable.

    Reads run_history (most recent first), skips runs with no route, and
    renders the last one through the Persian reporter so the speech says
    WHAT was made, in numbers, not a vague echo.
    """
    db = DatabaseSuite(persistent=True)
    try:
        q = db.query(
            "SELECT command, route FROM run_history "
            "WHERE succeeded = 1 AND route != '' AND outcome_class IS NOT 'blocked_env' "
            "ORDER BY id DESC LIMIT 1"
        )
        rows = q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — seeding is a courtesy, never a blocker
        return None
    if not rows:
        return None
    row = rows[0]
    route = [c for c in str(row["route"]).split(",") if c]
    if not route:
        return None
    try:
        from universal_mind.persian_report import persian_report as _render

        report = _render({
            "command": row["command"],
            "route": route,
            "ok": True,
            "flows": [],
            "result": {},
        })
    except Exception:  # noqa: BLE001 — fall back to the plain sentence
        report = f"آخرین کار موفق: {row['command']}"
    return {
        "text": report,
        "source": "history",
        "proven": True,
    }


def seed_for_capability(capability: str) -> dict[str, Any] | None:
    """Which capabilities may take the last run as their material."""
    if capability in ("speech", "clipboard", "notify"):
        return last_spoken_material()
    return None


__all__ = ["last_spoken_material", "seed_for_capability"]