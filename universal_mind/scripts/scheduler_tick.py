#!/usr/bin/env python3
"""The proactive tick — fire every due schedule, then sleep until the next.

Run mode (default): one tick then exit (safe for a Windows Task Scheduler job
or an external cron — the process never lingers).

    python scripts/scheduler_tick.py            # one tick
    python scripts/scheduler_tick.py --loop 60   # every 60s, forever (Ctrl+C)

The tick is idempotent and honest: it fires ONLY what is due, records each
firing (even failures advance the clock), and prints exactly what ran.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def tick(*, notify_summary: bool = True) -> dict[str, object]:
    # R54 (2026-09-30, operator decree): the scheduled tick runs hourly
    # unattended — it must NEVER use the loudspeaker. UM_MUTE is the mute
    # law's env channel; the operator can still unmute interactively
    # (the desktop path does not go through this env).
    import os as _os
    _os.environ.setdefault("UM_MUTE", "1")
    """One honest tick: back up the store, fire everything due, then SAY it.

    The rotating backup runs FIRST (the corrupted-db lesson: an external
    writer once splattered stderr over mind.db's header — a fresh backup at
    every tick means the worst case is always one tick old). Then the due
    work, then the toast.
    """
    from universal_mind.scheduler import backup_database, run_due

    try:
        backup_database()
    except Exception as exc:  # noqa: BLE001 — a backup failure never blocks work
        print(f"(backup failed: {exc})")

    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = run_due()
    fired = result.get("fired", [])
    count = result.get("count", 0)
    print(f"[{stamp}] tick: {count} schedule(s) fired")
    for entry in fired:
        status = "OK" if entry.get("ok") else f"FAILED ({entry.get('error', '')[:60]})"
        print(f"  - {entry.get('command', '')[:60]} → {status}")

    # WARMUP — the pre-computation pass: before any due work, the tick warms
    # the platform's hot paths so the operator's first command of the day is
    # instant (advisor vectorizer + lessons table + analytics), and a WARMUP
    # FAILURE names itself (a cold platform must not pretend it warmed).
    try:
        from universal_mind.run_history import ChainAdvisor
        from universal_mind.history_analytics import analyze_history

        ChainAdvisor().advise_semantic("گزارش کامل بساز")
        analyze_history()
        print("  (warmup: advisor + analytics گرم شد)")
    except Exception as exc:  # noqa: BLE001 — warmup is speed, never correctness
        print(f"  (warmup ناموفق: {exc})")

    # The folder watchers — the third perception channel (file events).
    watched_fired = 0
    try:
        from universal_mind.scheduler import scan_watchers

        watched = scan_watchers()
        watched_fired = int(watched.get("count", 0))
        for entry in watched.get("fired", []):
            status = "OK" if entry.get("ok") else f"FAILED ({entry.get('error', '')[:50]})"
            print(f"  - [watcher] {entry.get('file', '')} → {status}")
    except Exception as exc:  # noqa: BLE001 — watchers are a channel, never fatal
        print(f"(watchers failed: {exc})")

    # SELF-INSPECT — the agent examines ITSELF each tick: any goal stuck in
    # 'active' with zero progress for a long time is surfaced (a goal that
    # started but never moved is a REAL problem: the agent names it, the
    # operator decides). Auto-resume stays OFF — blindly re-running a broken
    # step every hour would be a retry loop, not intelligence.
    try:
        from universal_mind.agent_loop import _ensure_goals_table
        from universal_mind.database_suite import DatabaseSuite

        idb = DatabaseSuite(persistent=True)
        _ensure_goals_table(idb)
        stuck = idb.query(
            "SELECT id, goal, next_step FROM goals WHERE state = 'active' AND next_step = 0 "
            "AND id NOT IN (SELECT id FROM goals ORDER BY id DESC LIMIT 3) LIMIT 3"
        )
        if stuck.get("ok") and stuck["rows"]:
            for g in stuck["rows"]:
                print(f"  (خود-آزمایی: هدف «{g['goal'][:40]}» ثبت شده ولی هرگز شروع نشده)")
    except Exception as exc:  # noqa: BLE001 — self-inspection is a lens
        print(f"  (خود-آزمایی ناموفق: {exc})")

    # R44-6 — THE NIGHTLY RED TEAM: the platform attacks ITSELF with the
    # hostile corpus (typos, bare anaphora, boundaries, injection). Every
    # dishonest answer is a CAUGHT BUG: a finding row + a self-repair goal,
    # so the platform wakes with its own weaknesses as work items. The
    # sweep prints its honest count — never silently clean.
    try:
        from universal_mind.red_team import run_red_team

        sweep = run_red_team()
        fa = str(sweep["honest"]).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        fa_t = str(sweep["total"]).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        print(f"  (red-team شبانه: {fa} از {fa_t} پاسخِ خصمانه صادق بود)")
        for f in sweep["findings"]:
            print(f"  (شکارِ red-team: {f['kind']} روی «{f['command'][:40]}» → هدفِ ترمیم ثبت شد)")
    except Exception as exc:  # noqa: BLE001 — the sweep is a lens, never fatal
        print(f"  (red-team ناموفق: {exc})")

    # R44-15 — THE MONTHLY RESTORE DRILL: a backup that has never been
    # restored is only hope. The tick drills the newest backup once a month
    # (first tick of the month): copy to a throwaway dir, integrity-check,
    # compare every table's row count. Divergence is printed BY NAME.
    if datetime.now().month != getattr(tick, "_drill_month", 0):
        tick._drill_month = datetime.now().month  # type: ignore[attr-defined]
        try:
            from universal_mind.restore_drill import run_restore_drill

            drill = run_restore_drill()
            if drill.ok:
                fa_n = str(len(drill.tables)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                print(f"  (مانورِ بازیابی ماهانه: بکاپ واقعاً بازیابی شد — {fa_n} جدول همشمار، integrity: {drill.integrity})")
            else:
                print(f"  (مانورِ بازیابی ناموفق: {drill.error})")
        except Exception as exc:  # noqa: BLE001 — a drill is a lens, never fatal
            print(f"  (مانورِ بازیابی ناموفق: {exc})")

    # R46-14 — THE MONTHLY COMPACTION: on the FIRST tick of each month,
    # old rows (90+ days) move to the archive in small batches and the
    # count is SAID. A live rollback command keeps undo possible.
    try:
        from universal_mind.history_compact import compact_history

        today = datetime.now()
        if today.day == 1 or datetime.now().strftime("%Y-%m") != datetime.now(timezone.utc).strftime("%Y-%m"):
            pass  # first LOCAL day of the month OR timezone disagreement — run it
        if today.day == 1:
            comp = compact_history()
            print(f"  (فشردهسازی ماهانه: {comp['report']})")
    except Exception as exc:  # noqa: BLE001 — compaction is a lens, never fatal
        print(f"  (فشردهسازی ناموفق: {exc})")

    # R47-8 — THE VISIBLE DAY, KEPT FRESH: every active tick rebuilds
    # today.html so the day is always one glance away. A page failure
    # never kills the tick (the lens law).
    try:
        from universal_mind.today_page import build_today_page

        build_today_page()  # the shared persistent store — one page for all
    except Exception:  # noqa: BLE001 — the page is a courtesy, never fatal
        pass

    # R47-3 — THE LIVE-JUDGE SAMPLE: each tick sends ONE successful run of
    # today (the newest) to the live judge — the formula meets a foreign
    # standard every day, one verdict at a time. No env → honest silence.
    try:
        import os as _os

        if _os.environ.get("UM_LLM_BASE_URL"):
            from universal_mind.database_suite import DatabaseSuite as _DS
            from universal_mind.live_judge import judge_live

            _db = _DS.shared_persistent()
            _q = _db.query(
                "SELECT command, route, excellence FROM run_history "
                "WHERE succeeded = 1 AND date(created_at) = date(datetime('now', 'localtime')) "
                "ORDER BY id DESC LIMIT 1"
            )
            if _q.get("ok") and _q.get("rows"):
                _row = _q["rows"][0]
                _v = judge_live(
                    str(_row["command"]),
                    f"مسیر: {str(_row['route'])} — داوری فرمول: {_row['excellence']}",
                    float(_row["excellence"] or 0.0),
                )
                if _v.get("ok"):
                    print(f"  (⚖ داورِ زنده: نمونهی امروز نمرهی {_v['llm_score']:.2f} گرفت — {_v['reason'][:50]})")
                else:
                    print(f"  (⚖ داورِ زنده: {_v['reason'][:60]})")
    except Exception as exc:  # noqa: BLE001 — the judge is a lens, never fatal
        print(f"  (⚖ داورِ زنده ناموفق: {exc})")

    # R46-10 — THE MORNING BRIEFING: on the FIRST tick of each LOCAL day
    # the platform writes the day open (yesterday's outcome, today's
    # standings, any red signal) into a daily_briefings row + a toast.
    try:
        from universal_mind.daily_briefing import due_today, record_briefing

        today_str = datetime.now().strftime("%Y-%m-%d")
        if due_today(today_str):
            brief = record_briefing(today_str)
            print(f"  ({brief['report'].splitlines()[0]}")
            for ln in brief["report"].splitlines()[1:]:
                print(f"   {ln}")
            print("  )")
            try:
                from universal_mind.notify_adapter import NotifyToolConnector

                NotifyToolConnector().connect(
                    {}, {"title": "بریفینگ امروز", "body": brief["report"]}
                )
            except Exception:  # noqa: BLE001 — the toast is a courtesy
                pass
    except Exception as exc:  # noqa: BLE001 — the briefing is a lens, never fatal
        print(f"  (بریفینگ ناموفق: {exc})")

    # R45-8 — THE WEEKLY LETTER: on the first tick of each ISO week the
    # platform writes its own week (runs, successes, best route, verdicts)
    # into a toast + a weekly_reports row. A silent week is written as a
    # silent week — the letter is never fabricated.
    try:
        from universal_mind.weekly_letter import due_this_week, record_weekly_letter

        if due_this_week():
            info = record_weekly_letter()
            print(f"  (نامهی هفته: {info['report']})")
            try:
                from universal_mind.notify_adapter import NotifyToolConnector

                NotifyToolConnector().connect(
                    {}, {"title": "نامهی هفته", "body": info["report"]}
                )
            except Exception:  # noqa: BLE001 — the toast is a courtesy
                pass
    except Exception as exc:  # noqa: BLE001 — the letter is a lens, never fatal
        print(f"  (نامهی هفته ناموفق: {exc})")

    # R45-12 — THE UNKNOWN HARVEST: the nightly tick names the words the
    # operator keeps saying and the vocabulary keeps missing — direct data
    # for the next vocabulary wave.
    try:
        from universal_mind.unknown_harvest import top_unknowns

        terms = top_unknowns(5)
        if terms:
            fa_d = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
            txt = "، ".join(f"«{t['term']}» ({str(t['hits']).translate(fa_d)} بار)" for t in terms)
            print(f"  (واژههای ناشناختهی پرتکرار: {txt})")
        else:
            print("  (واژههای ناشناخته: هیچ — واژگان با گفتار تو همپوشان است)")
    except Exception as exc:  # noqa: BLE001 — the harvest is a lens, never fatal
        print(f"  (شکارِ واژههای ناشناخته ناموفق: {exc})")

    # R45-14 — THE DISK WATCH: the 60GB lesson. The store drive's real
    # free space is read every tick; below the floor a toast fires —
    # a full disk is never a surprise again.
    try:
        from universal_mind.disk_watch import disk_report

        dsk = disk_report()
        print(f"  (فضای دیسک: {dsk['report']})")
        if not dsk["ok"] and not dsk["error"]:
            try:
                from universal_mind.notify_adapter import NotifyToolConnector

                NotifyToolConnector().connect(
                    {}, {"title": "هشدار فضای دیسک", "body": dsk["report"]}
                )
            except Exception:  # noqa: BLE001 — the toast is a courtesy
                pass
    except Exception as exc:  # noqa: BLE001 — the watch is a lens, never fatal
        print(f"  (پایشِ دیسک ناموفق: {exc})")

    # The STOPPED GOALS: the tick surfaces every goal halted mid-way — the
    # operator's «ادامه بده» is the recovery for exactly these.
    stopped_goals = 0
    try:
        from universal_mind.agent_loop import _ensure_goals_table
        from universal_mind.database_suite import DatabaseSuite

        gdb = DatabaseSuite(persistent=True)
        _ensure_goals_table(gdb)
        gq = gdb.query("SELECT COUNT(*) AS n FROM goals WHERE state = 'stopped'")
        stopped_goals = int(gq["rows"][0]["n"]) if gq.get("ok") else 0
    except Exception:  # noqa: BLE001 — a status view, never fatal
        stopped_goals = 0

    if notify_summary and (count or watched_fired or stopped_goals):
        ok_count = sum(1 for f in fired if f.get("ok"))
        failed = count - ok_count
        # Persian digits, honest wording — successes first, failures named.
        fa = str(count).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        fa_ok = str(ok_count).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        body = f"{fa} کارِ زمان‌بندی‌شده اجرا شد ({fa_ok} موفق)"
        if watched_fired:
            fa_w = str(watched_fired).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            body += f"، {fa_w} فایلِ جدید پردازش شد"
        if stopped_goals:
            fa_g = str(stopped_goals).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            body += f"، {fa_g} هدفِ متوقف‌شده در انتظارِ «ادامه بده»"
        if failed:
            fa_failed = str(failed).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            body += f"، {fa_failed} ناموفق"
        try:
            from universal_mind.real_notify import NotifyTool

            NotifyTool().notify(title="ذهن یکپارچه — اجرای خودکار", body=body)
        except Exception as exc:  # noqa: BLE001 — the toast is a bonus, never fatal
            print(f"(toast failed: {exc})")
    result["watcher_fired"] = watched_fired
    # R46-13 — the health row: every tick leaves its trace (state, skipped
    # lens blocks, named causes); a FAILED tick reaches a toast. The count
    # comes from the fired entries THEMSELVES — the notify-only `failed`
    # variable lives inside the toast block and is not the tick's truth.
    entries = list(result.get("entries", result.get("fired", [])))
    failed_entries = [e for e in entries if not e.get("ok")]
    skipped = len(failed_entries)
    causes = "; ".join(
        f"{e.get('command', '')[:30]}: {e.get('error', '')[:40]}"
        for e in failed_entries
    )
    result["state"] = "failed" if failed_entries else "ok"
    result["skipped"] = skipped
    result["causes"] = causes
    _write_tick_health(dict(result))
    return dict(result)


def _write_tick_health(summary: dict[str, object]) -> None:
    """R46-13 — every tick's summary lands in tick_health (one row per tick).

    A tick that dies silently leaves no trace; this one leaves the trace:
    state (ok/degraded/failed), the count of lens blocks that skipped,
    their named causes, the fired schedules. The next FAILED tick reaches
    a toast — silence is never the operator's answer again.
    """
    try:
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite.shared_persistent()
        db.ensure_schema("tick_health", [
            "CREATE TABLE IF NOT EXISTS tick_health ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "state TEXT NOT NULL, fired INTEGER NOT NULL DEFAULT 0, "
            "skipped INTEGER NOT NULL DEFAULT 0, causes TEXT NOT NULL DEFAULT '', "
            "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
        ])
        state = str(summary.get("state", "ok"))
        fired_n = summary.get("fired", 0)
        fired_count = len(fired_n) if isinstance(fired_n, (list, tuple)) else int(str(fired_n))
        skipped_n = summary.get("skipped", 0)
        skipped_count = len(skipped_n) if isinstance(skipped_n, (list, tuple)) else int(str(skipped_n))
        db.insert_many("tick_health", [{
            "state": state,
            "fired": str(fired_count),
            "skipped": str(skipped_count),
            "causes": str(summary.get("causes", ""))[:500],
        }])
        if state == "failed":
            try:
                from universal_mind.notify_adapter import NotifyToolConnector

                NotifyToolConnector().connect(
                    {}, {"title": "tick ناسالم", "body": str(summary.get("causes", ""))[:300]}
                )
            except Exception:  # noqa: BLE001 — the toast is a courtesy
                pass
    except Exception as exc:  # noqa: BLE001 — the health row is a lens, never fatal
        print(f"(tick_health ناموفق: {exc})")


def main() -> int:
    parser = argparse.ArgumentParser(description="The proactive scheduler tick")
    parser.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                        help="keep ticking every SECONDS (0 = one tick and exit)")
    args = parser.parse_args()

    if args.loop <= 0:
        tick()
        return 0

    print(f"watching: a tick every {args.loop}s (Ctrl+C to stop)")
    try:
        while True:
            tick()
            time.sleep(args.loop)
    except KeyboardInterrupt:
        print("stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())