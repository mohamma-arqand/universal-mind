"""The unknown-noise purge — one honest cleanup, and a law for the future.

R45 item 9: 2,701 run_history rows carry route='' and no outcome_class —
all of them are synthetic dry-run leftovers from the platform's own test
era («این فرمان هیچ قابلیتی ندارد XY», «تو در تو», ...). They are DATA
POISON: every learning statistic (windows, letters, advisor) counted them
as real work.

The cleanup is a ONE-TIME reported migration, not a hidden filter:
1. backfills outcome_class='unknown_noise' on exactly those rows,
2. excludes that class from every learning stat (already wired into
   time_windows and weekly_letter via _EXCLUDE),
3. prints the before/after counts so the operator sees the real damage,
4. and from now on a run with no route is ALWAYS classified (the writer
   in run_history now stamps 'unknown_noise' when route is empty and no
   class was given) — poison can never silently return.
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def purge_unknown_noise(*, db: DatabaseSuite | None = None, apply: bool = False) -> dict[str, Any]:
    """Backfill 'unknown_noise' on route-less, class-less rows.

    apply=False is the DRY RUN: counts only, no writes. The report is the
    same either way — the operator decides with eyes open.
    """
    store = db or DatabaseSuite.shared_persistent()
    before_q = store.query(
        "SELECT COUNT(*) AS n FROM run_history "
        "WHERE route = '' AND (outcome_class IS NULL OR outcome_class = '')"
    )
    rows = before_q.get("rows", []) if before_q.get("ok") else []
    before = int(rows[0]["n"]) if rows else 0
    result: dict[str, Any] = {
        "ok": True,
        "dry_run": not apply,
        "rows_found": before,
        "rows_updated": 0,
        "error": "",
    }
    if apply and before:
        store.execute(
            "UPDATE run_history SET outcome_class = 'unknown_noise' "
            "WHERE route = '' AND (outcome_class IS NULL OR outcome_class = '')"
        )
        after_q = store.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE route = '' AND (outcome_class IS NULL OR outcome_class = '')"
        )
        rows2 = after_q.get("rows", []) if after_q.get("ok") else []
        result["rows_updated"] = before - (int(rows2[0]["n"]) if rows2 else 0)
    result["report"] = (
        f"{_fa(result['rows_found'])} ردیفِ بدونِ مسیر و بدونِ کلاس پیدا شد"
        + (f" — {_fa(result['rows_updated'])} ردیف به «unknown_noise» علامت خورد."
           if apply else " — حالت خشک؛ برای اعمال، apply=True بده.")
    )
    return result


if __name__ == "__main__":  # pragma: no cover — the operator's one-time run
    import argparse

    ap = argparse.ArgumentParser(description="Purge the unknown-noise rows.")
    ap.add_argument("--apply", action="store_true", help="really write (default: dry run)")
    args = ap.parse_args()
    info = purge_unknown_noise(apply=args.apply)
    print(info["report"])
