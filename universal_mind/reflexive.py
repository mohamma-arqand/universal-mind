"""The reflexive class — questions the platform answers about ITSELF.

«چند تا اجرا موفق داشتی؟» / «موفقترین قابلیت کدومه؟» / «کدام زنجیره...» —
these are not commands to run a capability; they are questions about the
platform's own real store. The answer must be a REAL number from
run_history, never a guess, never a vague "many".

Six honest reflexes, each backed by one SQL sentence:
  - n runs / n successes / n failed
  - n goals by state
  - the most successful chain (with its real win count)
  - the most successful capability (aggregate over chains)
  - the last thing made (the newest successful run's command)
  - the help line (the capability list, counted for real)
"""

from __future__ import annotations

from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa_num(value: int | float | str) -> str:
    return str(value).translate(_FA)


_FA_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
    7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند",
}


def _windows_uptime_fa() -> str:
    """The REAL uptime from WMI LastBootUpTime, in Persian words.

    An unreadable WMI is honest («نمیدانم»), never a fabricated number.
    """
    try:
        import subprocess

        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss')"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        raw = (out.stdout or "").strip()
        if out.returncode != 0 or not raw or "T" not in raw and "-" not in raw:
            return "مدت روشنبودن دستگاه را نتوانستم بخوانم."
        from datetime import datetime

        # CIM prints locale-dependent text by default; we asked for ISO —
        # take the leading 19 chars either way and parse.
        boot = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - boot
        days, seconds = delta.days, delta.seconds
        hours, minutes = seconds // 3600, (seconds % 3600) // 60
        parts = []
        if days:
            parts.append(f"{_fa_num(days)} روز")
        if hours:
            parts.append(f"{_fa_num(hours)} ساعت")
        if minutes and not days:
            parts.append(f"{_fa_num(minutes)} دقیقه")
        return "دستگاه " + " و ".join(parts) + " است که روشن است."
    except Exception:  # noqa: BLE001 — the reflex never crashes the router
        return "مدت روشنبودن دستگاه را نتوانستم بخوانم."


def _query(db: DatabaseSuite, sql: str) -> list[dict[str, Any]]:
    try:
        q = db.query(sql)
        return q.get("rows", []) if q.get("ok") else []
    except Exception:  # noqa: BLE001 — a reflex never crashes the router
        return []


def answer_reflexive(command: str) -> dict[str, Any] | None:
    """Route a self-question to its real answer — or None (not reflexive).

    None means the command is NOT a question about the platform; the
    ordinary router continues. A matched reflex NEVER runs a capability —
    it reads the store and answers.
    """
    db = _store()
    c = command.strip()

    # R58 M3 — RECALL THE NAMED MEMORY BY ASKING: «جلسه شنبه چه ساعتی است؟»
    # The sweep measured that «یادت باشد جلسه شنبه ساعت ۱۰ است» SAVES a
    # named_memory row, but asking the question back got «نشناختم». A
    # question whose words overlap a stored fact is answered FROM that fact
    # — never invented. Multiple hits are NAMED, not guessed.
    _QUESTION_MARKS = ("چیه", "چیست", "چی بود", "چه ساعتی", "کجاست", "کی بود",
                       "چند ساعته", "چیه؟", "کجاست؟")
    if any(m in c for m in _QUESTION_MARKS) and "یادت باشد" not in c:
        try:
            _facts = _query(db, "SELECT fact FROM named_memory ORDER BY id DESC LIMIT 200")
        except Exception:  # noqa: BLE001 — memory is a lens, never fatal
            _facts = []
        _stop = {"چه", "چیه", "چیست", "چی", "ساعتی", "کجاست", "کی", "بود", "است",
                 "راست", "را", "؟", "؟", "جلسه", "چند", "ساعت"}
        _words = [w for w in c.replace("؟", " ").replace("؟", " ").split()
                  if len(w) > 2 and w not in _stop]
        _hits = []
        for _f in _facts:
            _fact = str(_f["fact"])
            _shared = [w for w in _words if w in _fact]
            if len(_shared) >= max(1, min(2, len(_words))):
                _hits.append((_fact, len(_shared)))
        if len(_hits) == 1:
            return _reflex_answer(
                c, f"یادم است: «{_hits[0][0]}» — (از حافظهٔ نامدار خواندم)",
            )
        if len(_hits) > 1:
            _named = "؛ ".join(f"«{h[0]}»" for h in _hits[:4])
            return _reflex_answer(
                c, f"چند مورد یادم آمد: {_named} — کدام را می‌خواهی دقیق بگویم؟",
            )
        # no hit: fall through — maybe another reflex class knows the answer

    # R59 P6 — MY CHAINS: «زنجیره‌های من را نشان بده» — the sweep measured
    # «نشناختم» while ChainsStore().load() existed. The listing names each
    # saved chain and its REAL steps (validated against the registry on
    # load); empty is honest with the recipe for saving one.
    if ("زنجیره" in c and ("زنجیره‌های من" in c or "زنجیرههای من" in c
                           or "زنجیره‌هام" in c or "زنجیرههام" in c)) \
            and any(w in c for w in ("نشان", "لیست", "فهرست", "چی", "دارم", "بگو")):
        from universal_mind.chains_store import ChainsStore

        try:
            from universal_mind.database_suite import DatabaseSuite as _DS

            saved = ChainsStore(db=_DS.shared_persistent()).load()
        except Exception as exc:  # noqa: BLE001 — a listing is a lens, never fatal
            return _reflex_answer(c, f"خواندن زنجیره‌ها نشد: {exc}")
        if not saved:
            return _reflex_answer(
                c, "هنوز زنجیره‌ای ذخیره نکردی — مثلا: «زنجیره‌ی گزارش هفتگی را ذخیره کن».",
            )
        chain_lines = [f"{_fa_num(len(saved))} زنجیره ذخیره شده:"]
        # the Persian capability names from the ONE source of truth
        # (persian_report._CAP_FA) — never a second translation table
        try:
            from universal_mind.persian_report import _CAP_FA as _CAP_FA_NAME
        except Exception:  # noqa: BLE001
            _CAP_FA_NAME = {}
        for i, ch in enumerate(saved, start=1):
            steps_fa = " ← ".join(_CAP_FA_NAME.get(s, s) for s in ch.capabilities)
            chain_lines.append(f"  {_fa_num(i)}. {ch.name} — {steps_fa}")
        return _reflex_answer(c, "\n".join(chain_lines))

    # R59 P5 — MEMORY LISTINGS: «چه چیزهایی یادت هست؟» / «آخرین چیزی که یادت
    # داشت چی بود؟» — the sweep measured both dying in «نشناختم» while
    # named_memory already had recall_facts(). A LIST is not a recall-by-
    # question (M3): no question marks needed, just the real rows, numbered.
    if ("چه چیزهایی یادت" in c or "چی یادته" in c or "یادت هست" in c
            or "یادداشتهایت" in c or "یادداشت‌هایت" in c) and "یادت باشد" not in c:
        from universal_mind.named_memory import recall_facts

        rows = []
        try:
            rows = recall_facts(limit=10)
        except Exception:  # noqa: BLE001 — the listing is a lens, never fatal
            rows = []
        if not rows:
            return _reflex_answer(
                c, "هیچ چیزی یادم نیست — «یادت باشد …» بگو تا نگه دارم.",
            )
        lines = [f"{_fa_num(len(rows))} چیز یادم است:"]
        for i, r in enumerate(rows, start=1):
            lines.append(f"  {_fa_num(i)}. {str(r['fact'])}")
        return _reflex_answer(c, "\n".join(lines))

    if ("آخرین چیزی که یادت" in c or "آخرین یادداشت" in c) and "یادت باشد" not in c:
        from universal_mind.named_memory import recall_facts

        rows = []
        try:
            rows = recall_facts(limit=1)
        except Exception:  # noqa: BLE001
            rows = []
        if not rows:
            return _reflex_answer(
                c, "هیچ چیزی یادم نیست — «یادت باشد …» بگو تا نگه دارم.",
            )
        return _reflex_answer(c, f"آخرین چیزی که یاد داشتم: «{rows[0]['fact']}».")

    # R59 P3+P4 — MACHINE VIEWS: «چه برنامه‌هایی الان باز است؟» and
    # «پروسه‌های پرمصرف را نشان بده» — two measured dead sentences. Both are
    # READ-ONLY PowerShell views of the real machine (the same CIM path the
    # uptime uses). A PowerShell failure is surfaced by name, never faked.
    if ("چه برنامه" in c or "چه پنجره" in c or "پنجره‌های باز" in c
            or "برنامه‌های باز" in c):
        from universal_mind.window_view import list_open_windows, windows_fa

        res = list_open_windows()
        return _reflex_answer(c, windows_fa(res))
    if ("پروسه" in c or "پردازش" in c or "پروسس" in c) and any(
        w in c for w in ("پرمصرف", "سنگین", "مصرف", "نشان بده", "ram", "رم", "cpu")
    ):
        from universal_mind.window_view import processes_fa, top_processes

        res = top_processes(5)
        return _reflex_answer(c, processes_fa(res))

    # R58 M4 — THE UPCOMING AGENDA: «برنامه‌ام را نشان بده» / «هفتهٔ بعد چی
    # کار دارم؟» — the sweep measured that no view exists of what is COMING.
    # The truth already lives in two tables: schedules (repeating + one-shot
    # reminders) and named_memory (notes that mention a time). Read-only,
    # sorted by when, Persian; empty is said honestly.

    _AGENDA_WORDS = ("برنامه‌ام", "برنامهام", "برنامهٔ من", "برنامه من",
                     "برنامه‌ی من", "هفتهٔ بعد", "هفته بعد")
    if any(w in c for w in _AGENDA_WORDS) and any(
        q in c for q in ("نشان بده", "بگو", "چی", "چه", "دارم", "است", "لیست")
    ):
        from universal_mind.scheduler import list_schedules

        agenda_lines: list[str] = []
        # ۱) one-shot reminders, soonest first
        try:
            upcoming = [s for s in list_schedules()
                        if s.kind == "once" and s.active and s.run_at]
            for s in sorted(upcoming, key=lambda s: s.run_at):
                agenda_lines.append(f"• یادآور «{s.command}» — زمان {s.run_at}")
        except Exception:  # noqa: BLE001 — the agenda is a lens, never fatal
            pass
        # ۲) repeating schedules (the daily/periodic backbone)
        try:
            for s in list_schedules():
                if s.kind != "once" and s.active:
                    if s.hour_of_day >= 0:
                        agenda_lines.append(
                            f"• هر روز ساعت {_fa_num(f'{s.hour_of_day:02d}:{s.minute_of_hour:02d}')} — «{s.command}»")
                    else:
                        agenda_lines.append(f"• هر {_fa_num(s.every_minutes)} دقیقه — «{s.command}»")
        except Exception:  # noqa: BLE001
            pass
        # ۳) named notes that mention a time word (the soft agenda)
        try:
            for r in _query(db, "SELECT fact FROM named_memory ORDER BY id DESC LIMIT 100"):
                fact = str(r["fact"])
                if any(t in fact for t in ("ساعت", "شنبه", "یکشنبه", "دوشنبه",
                                           "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه",
                                           "فردا", "امروز")):
                    agenda_lines.append(f"• (یادداشت) {fact}")
        except Exception:  # noqa: BLE001
            pass

        if not agenda_lines:
            return _reflex_answer(
                c, "هیچ برنامه‌ای ثبت نشده — «یادم بنداز که …» یا «یادآور کن …» بگو.",
            )
        return _reflex_answer(c, "برنامه‌ات:\n" + "\n".join(agenda_lines))

    # «چند تا اجرا موفق داشتی؟» — the run counts, real.
    # N10-3 (R57): «چند فرمان اجرا کردی؟» — the same question in the other
    # spoken shape, measured live in the night's 14-command sweep.
    if "چند تا" in c or "چندتا" in c or "چند فرمان" in c or "چند تا فرمان" in c:
        if "هدف" in c:
            rows = _query(db, "SELECT state, COUNT(*) AS n FROM goals WHERE state != 'archived' GROUP BY state")
            if not rows:
                return _reflex_answer(c, "هنوز هدفی ثبت نشده.")
            parts = [f"{state_fa(r['state'])}: {_fa_num(r['n'])}" for r in rows]
            return _reflex_answer(c, "هدفها — " + "، ".join(parts))
        total = _query(db, "SELECT COUNT(*) AS n FROM run_history")
        ok_n = _query(db, "SELECT COUNT(*) AS n FROM run_history WHERE succeeded = 1")
        n = int(total[0]["n"]) if total else 0
        okc = int(ok_n[0]["n"]) if ok_n else 0
        return _reflex_answer(
            c,
            f"{_fa_num(n)} اجرا ثبت شده؛ {_fa_num(okc)} موفق ({_fa_num(round(100 * okc / n) if n else 0)}٪).",
        )

    # «موفقترین زنجیره/قابلیت کدومه؟» — the real ranking.
    if "کدام" in c or "کدوم" in c or "موفقترین" in c:
        rows = _query(
            db,
            "SELECT route, COUNT(*) AS n FROM run_history "
            "WHERE succeeded = 1 AND route != '' GROUP BY route ORDER BY n DESC LIMIT 1",
        )
        if not rows:
            return _reflex_answer(c, "هنوز اجرای موفقی ثبت نشده.")
        if "قابلیت" in c:
            cap_rows = _query(
                db,
                "SELECT route FROM run_history WHERE succeeded = 1 AND route != ''",
            )
            counts: dict[str, int] = {}
            for r in cap_rows:
                for cap in str(r["route"]).split(","):
                    cap = cap.strip()
                    if cap:
                        counts[cap] = counts.get(cap, 0) + 1
            if not counts:
                return _reflex_answer(c, "هنوز قابلیتی اجرا نشده.")
            best = max(counts, key=lambda k: counts[k])
            return _reflex_answer(c, f"موفقترین قابلیت: {best} ({_fa_num(counts[best])} اجرا).")
        return _reflex_answer(
            c,
            f"موفقترین زنجیره: {rows[0]['route']} با {_fa_num(rows[0]['n'])} برد.",
        )

    # «ترندها رو نشون بده» — the session's REAL trend, not a guess: the
    # daily excellence verdict already computed by history_analytics.
    if "ترند" in c or "روند" in c:
        try:
            from universal_mind.history_analytics import session_verdict

            sv = session_verdict()
            if sv.get("ok"):
                mean_raw = sv.get("mean_excellence", sv.get("mean", 0))
                mean_pct = _fa_num(round(float(mean_raw) * 100))
                runs_n = _fa_num(sv.get("runs", 0))
                return _reflex_answer(
                    c,
                    f"روند داوری نشست: {sv['verdict']} — میانگین {mean_pct}٪ روی {runs_n} اجرا.",
                )
        except Exception:  # noqa: BLE001 — a reflex never crashes
            pass
        return _reflex_answer(c, "هنوز دادهی روندی ندارم — چند فرمان بده تا روند شکل بگیرد.")

    # «آخرین چیزی که ساختی؟» / «چیزی که قبلا ساختی رو نشونم بده» — the
    # newest real success, in ANY spoken shape (قبلا/این چند روز).
    # («دیروز» alone is a TIME WINDOW (R45-1) unless it asks to SHOW something.)
    if (
        ("آخرین" in c or "قبلا" in c or ("دیروز" in c and ("نشون" in c or "نشان" in c)))
        and ("ساختی" in c or "کردی" in c or "ساخت" in c)
    ):
        rows = _query(
            db,
            "SELECT command, route FROM run_history WHERE succeeded = 1 AND route != '' ORDER BY id DESC LIMIT 1",
        )
        if not rows:
            return _reflex_answer(c, "هنوز چیزی نساختهایم.")
        return _reflex_answer(c, f"آخرین کار موفق: «{rows[0]['command']}» ({rows[0]['route']}).")

    # R53 — «امروز چندمه؟ / امروز چه روزی است؟ / ساعت چنده؟» — the LOCAL
    # clock in the operator's own calendar (Jalali), real, from persian_date.
    # R58 M2 — RELATIVE DATES: «فردا چندمه؟» / «دیروز چه روزی بود؟» /
    # «پس‌فردا چندمه؟» — the same question about a NEIGHBOUR day, measured
    # in the 18-command sweep. jalali_date(offset_days) already exists; the
    # gate just never recognized the relative words.
    _RELATIVE_DAYS = [
        # ORDER MATTERS: longer words first — «پس‌فردا» contains «فردا»,
        # so a dict-ordered lookup would answer "فردا" for "پس‌فردا" (a live
        # witness caught exactly that). The longest match wins.
        ("پس‌فردا", 2),
        ("پسفردا", 2),
        ("پریروز", -2),
        ("فردا", 1),
        ("دیروز", -1),
    ]
    _asked_relative = None
    if any(w[0] in c for w in _RELATIVE_DAYS) and (
        "چندمه" in c or "چند مه" in c or "چه روزی" in c or "تاریخ" in c
        or "چندمه؟" in c or c.strip() in ("فردا؟", "دیروز؟")
    ):
        from universal_mind.persian_date import jalali_date as _jd

        for _w, _off in _RELATIVE_DAYS:
            if _w in c:
                _asked_relative = (_w, _off, _jd)
                break
    if _asked_relative is not None:
        _w, _off, _jd = _asked_relative
        _d = f"{_w} {_jd(_off)} است"
        if _off < 0:
            _d = f"{_w} {_jd(_off)} بود"
        return _reflex_answer(c, _d + ".")

    # R60 Q3 — TIME-UNTIL and WEEKDAY-DISTANCE, both measured in the 19-command
    # sweep: «چند دقیقه تا نیمه‌شب مانده؟» and «شنبه چند روز دیگه است؟».
    # The clock is REAL (datetime.now), the weekday is REAL (the local
    # calendar — Jalali context, Persian weekday names), and the answer
    # Persianizes every digit.
    if "مانده" in c or "مانده؟" in c or " مونده" in c or "مونده" in c:
        from datetime import datetime, timedelta

        _now = datetime.now()
        # نیمه‌شب — the coming midnight
        if "نیمه‌شب" in c or "نیمه شب" in c:
            _mid = _now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            _delta = _mid - _now
            _mins = int(_delta.total_seconds() // 60)
            _h, _m = divmod(_mins, 60)
            if _h > 0:
                _txt = f"تا نیمه‌شب {_fa_num(_h)} ساعت و {_fa_num(_m)} دقیقه مانده"
            else:
                _txt = f"تا نیمه‌شب {_fa_num(_mins)} دقیقه مانده"
            return _reflex_answer(c, _txt + ".")
        # «تا ساعت بعدی» — the next whole hour
        if "ساعت بعد" in c:
            _nx = (_now.replace(minute=0, second=0, microsecond=0)
                   + timedelta(hours=1))
            _mins = int((_nx - _now).total_seconds() // 60)
            return _reflex_answer(
                c, f"تا ساعت بعدی {_fa_num(_mins)} دقیقه مانده.")

    # R60 Q3 — «شنبه چند روز دیگه است؟» / «جمعه چند روز دیگه؟» — the REAL
    # weekday distance on the operator's calendar (Saturday starts the
    # Persian week). days_ahead computed from datetime.now().
    # ORDER MATTERS (the پس‌فردا/فردا law): «شنبه» is a SUBSTRING of
    # «یکشنبه/دوشنبه/سه‌شنبه/چهارشنبه» — the longer words must be tested
    # first or «یکشنبه چند روز دیگه» would answer «شنبه».
    _FA_WEEKDAYS = [
        ("سه‌شنبه", 1), ("سهشنبه", 1),
        ("یکشنبه", 6), ("دوشنبه", 0), ("چهارشنبه", 2),
        ("پنجشنبه", 3), ("پنج شنبه", 3),
        ("شنبه", 5), ("جمعه", 4),
    ]  # Python weekday(): Monday=0 … Sunday=6
    if "دیگه" in c or "دیگر" in c or ("مانده" in c and "هفته" in c):
        from datetime import datetime

        _wd = next((w for w, _ in _FA_WEEKDAYS if w in c), None)
        if _wd is not None:
            _now = datetime.now()
            _target = next(o for w, o in _FA_WEEKDAYS if w == _wd)
            _days_ahead = (_target - _now.weekday()) % 7
            if _days_ahead == 0:
                _txt = f"{_wd} امروز است."
            else:
                _txt = f"تا {_wd} {_fa_num(_days_ahead)} روز مانده."
            return _reflex_answer(c, _txt)


    if (
        ("امروز" in c and ("چندمه" in c or "چند مه" in c or "چه روزی" in c or "تاریخ" in c))
        or "تاریخ امروز" in c
        or c in ("تاریخ چنده؟", "تاریخ؟", "ساعت چنده؟", "ساعت چند است؟")
    ):
        from datetime import datetime

        from universal_mind.persian_date import jalali_date

        if "ساعت" in c:
            from datetime import datetime

            from universal_mind.persian_date import gregorian_to_jalali_parts

            now = datetime.now()
            jy, jm, jd = gregorian_to_jalali_parts(now.year, now.month, now.day)
            return _reflex_answer(
                c,
                f"ساعت {_fa_num(now.strftime('%H:%M'))} است — "
                f"امروز {_fa_num(jd)} {_FA_MONTHS.get(jm, '')}، تاریخ {jalali_date()}",
            )
        return _reflex_answer(c, f"امروز {jalali_date()} است.")

    # R60 Q5 — «تنظیماتت را نشان بده» — the operator's OWN preferences, from
    # the REAL store, read-only (changing one has its own sentence shape).
    # Secret-looking keys are masked in all_prefs(); the count stays honest.
    if (
        ("تنظیمات" in c or "تنظیماتت" in c or "ترجیحات" in c)
        and ("نشان" in c or "بگو" in c or "چیه" in c or "چیست" in c or "لیست" in c)
    ):
        from universal_mind import operator_preferences as _op

        prefs = _op.all_prefs()
        if not prefs:
            return _reflex_answer(
                c, "هیچ تنظیماتی ذخیره نکرده‌ام — با «X را Y کن» می‌سازم.")
        lines = [f"{_fa_num(len(prefs))} تنظیم ذخیره کرده‌ام:"]
        for k, v in prefs.items():
            lines.append(f"• {k} = {v}")
        return _reflex_answer(c, "\n".join(lines))

    # «چند وقته دستگاه روشن است؟» — the REAL Windows uptime (WMI), honest.
    if ("دستگاه" in c or "سیستم" in c or "کامپیوتر" in c) and (
        "روشن" in c and ("چند" in c or "وقت" in c or "مدت" in c)
    ):
        return _reflex_answer(c, _windows_uptime_fa())

    # «راهنما / چیکار میتونی بکنی؟ / چی بلدی؟ / قابلیتهات» — the list, counted.
    if (
        c in ("راهنما", "help")
        or "چیکار میتونی" in c
        or "چی کار میتونی" in c
        or "چه کار میتونی" in c
        or "چه کارهایی میتونی" in c
        or "چه کارهایی بلدی" in c
        or "چی بلدی" in c
        or "چه بلدی" in c
        or "قابلیتهات" in c
        or "قابلیت هات" in c
        or ("قابلیت" in c and ("نشون" in c or "بگو" in c or "لیست" in c or "فهرست" in c))
    ):
        from universal_mind.real_tool_registry import real_tool_registry

        caps = real_tool_registry().capabilities()
        return _reflex_answer(
            c,
            f"{_fa_num(len(caps))} قابلیت: " + "، ".join(caps),
        )

    # «امروز چی کار کردی؟ / امروز چه ساختی؟» — today's REAL runs, counted.
    if "امروز" in c and ("کار" in c or "ساختی" in c or "اجرا" in c or "کردی" in c):
        today = _query(
            db,
            "SELECT COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n FROM run_history "
            "WHERE date(created_at) = date('now', 'localtime') "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param'))",
        )
        n = int(today[0]["n"]) if today else 0
        n_ok = int(today[0]["ok_n"]) if today else 0
        if n == 0:
            return _reflex_answer(c, "امروز هنوز کاری انجام ندادهام — اولین فرمان را بده.")
        return _reflex_answer(
            c,
            f"امروز {_fa_num(n)} فرمان اجرا کردم؛ {_fa_num(n_ok)} موفق "
            f"({_fa_num(round(100 * n_ok / n) if n else 0)}٪).",
        )

    # R45-1 — TIME WINDOWS: «دیروز چی کار کردی؟» / «این هفته چطور بود؟» /
    # «ماه پیش چطور بود؟» — the same LOCAL-day law, three windows back.
    if any(w in c for w in ("دیروز", "هفته", "ماه پیش", "این ماه")) and (
        "کار" in c or "کردی" in c or "اجرا" in c or "چطور" in c or "بود" in c
    ):
        from universal_mind.time_windows import window_sentence

        for name in ("دیروز", "این هفته", "هفته پیش", "این ماه", "ماه پیش"):
            if name in c:
                try:
                    return _reflex_answer(c, window_sentence(name, db=db))
                except Exception:  # noqa: BLE001 — a time answer never crashes
                    return _reflex_answer(c, f"نمیتوانم {name} را از تاریخچه بخوانم.")

    # R45-3 — CHAT MEMORY: «آخرین گفتگویمان چه بود؟» — the REAL stored
    # conversation, replayed (up to 5 turns), with the same honest-zero law.
    if "گفتگو" in c and ("آخرین" in c or "چه بود" in c or "نشون" in c or "یادت" in c):
        from universal_mind.chat_history_store import message_count, recent_messages

        total_msgs = message_count()
        if total_msgs == 0:
            return _reflex_answer(c, "هنوز گفتگویی ثبت نشده — اولین کلمه را بگو.")
        msgs = recent_messages(5)
        if not msgs:
            return _reflex_answer(c, "گفتگو را نمیتوانم بخوانم.")
        _FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        lines = []
        for m in msgs:
            who = "من" if m["who"] == "من" else ("سیستم" if m["who"] == "سیستم" else m["who"])
            mark = "✅" if m["ok"] else ""
            lines.append(f"{who}: {m['text'][:80]}{' ' + mark if mark else ''}")
        return _reflex_answer(
            c,
            f"آخرین گفتگوی ما (از {str(total_msgs).translate(_FA)} پیام ثبتشده):\n"
            + "\n".join(lines),
        )

    # R45-12 — «چه واژههایی را نمیشناسی؟» — the harvest, read back.
    if "نمیشناس" in c and "واژه" in c:
        from universal_mind.unknown_harvest import unknown_sentence

        return _reflex_answer(c, unknown_sentence())

    # R47-10 — THE VOCABULARY SUGGESTS: «واژههای ناشناخته را پیشنهاد بده»
    # names each frequent unknown and its nearest REAL capability.
    if ("ناشناخته" in c and "پیشنهاد" in c) or "واژههای ناشناخته را پیشنهاد" in c:
        from universal_mind.vocab_breathing import suggestions

        items = suggestions(min_hits=1)
        if not items:
            return _reflex_answer(c, "واژهی ناشناختهی پرتکراری برای پیشنهاد نیست — شکار تمیز است.")
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        lines = []
        for it in items:
            lines.append(
                f"• «{it['term']}» ({str(it['hits']).translate(fa)} بار) — "
                f"شاید منظورت «{it['capability']}» بود؟ بگو: واژهی {it['term']} یعنی {it['capability']}"
            )
        return _reflex_answer(c, "واژههای ناشناخته و نزدیکترین قابلیت:\n" + "\n".join(lines))

    # R47-11 — THE LEARNING RATIO: «چقدر یاد گرفتی؟» answers with the real
    # share of harvested unknowns that are resolved — a number that grows.
    if "چقدر یاد گرفتی" in c or ("یاد" in c and "گرفتی" in c and "چقدر" in c):
        from universal_mind.vocab_breathing import learning_ratio, learning_fa

        info = learning_ratio()
        return _reflex_answer(c, learning_fa(info))

    # R45-11 — «پیشنهاد بده» — real advice from real runs.
    if "پیشنهاد" in c and ("بده" in c or "چی" in c or "کن" in c):
        from universal_mind.advisor_suggest import suggest

        info = suggest()
        return _reflex_answer(c, info["report"])

    # R46-15 — «بکاپ سالم است؟» — the recovery path's health, with proof:
    # the newest backup, the last drill's verdict, and an explicit warning
    # when the backup is stale (>7 days) or absent.
    if "بکاپ" in c or "بک آپ" in c:
        from universal_mind.backup_health import backup_health

        health = backup_health()
        return _reflex_answer(c, health["report"])

    # R46-12 — THE ONE-MENU PERIODIC REPORT: «گزارش کامل بده» (as a
    # QUESTION, not a chain command) returns EVERY periodic report — the
    # morning briefing, the weekly letter, the yearbook — in ONE
    # structured answer, each section from its REAL table.
    if c.strip().rstrip("!.؟") in ("گزارش دورهیای بده", "گزارش دوره ای بده",
                                    "گزارش کامل بده", "همهی گزارشها بده",
                                    "گزارش کامل"):
        from datetime import datetime as _dt

        from universal_mind.daily_briefing import record_briefing, today_briefing

        brief = today_briefing()
        if not brief:
            brief = record_briefing(_dt.now().strftime("%Y-%m-%d"))["report"]
        sections: list[str] = [brief]
        try:
            from universal_mind.weekly_letter import latest_letter

            letter = latest_letter()
            letter_text = str(letter.get("report", "")) if isinstance(letter, dict) else str(letter or "")
            if letter_text:
                sections.append("📬 " + letter_text)
        except Exception:  # noqa: BLE001 — a section is a lens
            pass
        try:
            from universal_mind.database_suite import DatabaseSuite as _DS
            from universal_mind.yearbook import build_yearbook

            yb = build_yearbook(db=_DS.shared_persistent())
            if isinstance(yb, dict) and yb.get("ok"):
                secs = yb.get("sections") or []
                text = " | ".join(str(s) for s in secs[:4])
            else:
                text = str(yb) if not isinstance(yb, dict) else ""
            if text:
                sections.append("📖 " + text)
        except Exception:  # noqa: BLE001 — a section is a lens
            pass
        return _reflex_answer(c, "\n\n".join(sections))

    # R46-10 — «بریفینگ امروز را بگو» — the morning briefing, read back.
    if "بریفینگ" in c:
        from universal_mind.daily_briefing import record_briefing, today_briefing
        from datetime import datetime as _dt

        stored = today_briefing()
        if not stored:
            # no briefing yet today → write it NOW from the real tables
            # (the operator asked; the day opens on the ask, not on a tick)
            info = record_briefing(_dt.now().strftime("%Y-%m-%d"))
            stored = info["report"]
        return _reflex_answer(c, stored)

    # R47-7 — THE VISIBLE DAY: «صفحهی امروز را بساز» renders today as
    # one live HTML page from the real tables and says WHERE it lives.
    if ("صفحهی امروز" in c or ("صفحه" in c and "امروز" in c and "بساز" in c)):
        from universal_mind.today_page import build_today_page

        info = build_today_page()
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        answer = (
            f"صفحهی امروز ساخته شد — {str(info['runs']).translate(fa)} فرمان، "
            f"{str(info['wins']).translate(fa)} موفق، "
            f"{str(info['shield']).translate(fa)} تأیید 🛡\n"
            f"📍 {info['path']}"
        )
        return _reflex_answer(c, answer)

    # R47-9 — THE FULL GOODBYE: «جمعبندی روز» counts the real day and
    # closes it — the count comes from run_history, never a promise.
    if "جمعبندی روز" in c or ("جمعبندی" in c and "امروز" in c):
        from universal_mind.today_page import build_today_page

        info = build_today_page()
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        answer = (
            f"🌙 جمعبندیِ امروز: {str(info['runs']).translate(fa)} فرمان اجرا شد، "
            f"{str(info['wins']).translate(fa)} موفق، "
            f"{str(info['shield']).translate(fa)} فایلِ تأییدشده، "
            f"{str(info['judgments']).translate(fa)} قضاوتِ زنده.\n"
            f"صفحهی امروز هم تازه شده: {info['path']}\n"
            "خداحافظ — فردا بریفینگ منتظرت است."
        )
        return _reflex_answer(c, answer)

    # R47-5 — THE PRE-RUN QUESTION: «آیا ... کار میکند؟ / احتمالش چقدر
    # است؟» — the predictor answers BEFORE any run happens. No execution,
    # no fabricated hope: the real prediction (chain evidence + semantic
    # anchor) is spoken, with its tier and its anchor named.
    if (("آیا" in c and "کار میکند" in c) or ("احتمالش چقدر است" in c)
            or ("احتمال موفقیت" in c)):
        from universal_mind.persian_router import route

        routed = route(c)
        chain = tuple(routed.capabilities or ())
        # the QUESTION FRAME is not the command: strip «آیا ... کار
        # میکند؟» so the predictor sees the core, not the scaffolding.
        # only the QUESTION FRAME is stripped — «را» and the rest of the
        # sentence are the operator's real words and stay in the core.
        core = c.replace("آیا", " ").replace("کار میکند", " ")
        core = core.replace("احتمالش چقدر است", " ").replace("؟", " ")
        core = core.replace("احتمال موفقیت", " ").replace("میشود", " ")
        core = core.replace("میکند", " ").strip() or c
        from universal_mind.semantic_predictor import predict_semantic, anchor_fa
        from universal_mind.success_predictor import prediction_fa

        pred = predict_semantic(core, chain)
        answer = prediction_fa(pred)
        if pred.semantic_anchor:
            answer += f"\n• {anchor_fa(pred.semantic_anchor)}"
        else:
            answer += "\n• فرمانِ مشابهی در تاریخچه پیدا نشد — پیشبینی از شواهدِ خودِ زنجیره است."
        return _reflex_answer(c, answer)

    # R45-10 — «وضعیت خودت چطور است؟» — five live signals, one answer.
    # R46-8 — FREE-FORM STATUS ASKS: «خب؟ / چی جدید؟ / وضع؟ / خبر چیست؟»
    # reach the SAME five-signal answer — BUT the bare «وضعیت» (the
    # operator's BOARD command) keeps its own goal route: a free-form
    # alias never steals a command with its own richer meaning.
    if ("وضعیت خود" in c or "حالت خود" in c or ("سلامتی" in c and "خود" in c)
            or ("وضعیت" in c and "چطور" in c and "خود" in c)
            or c.strip().rstrip("?.!؟") in ("خب", "چی جدید", "وضع", "خبر چیست",
                                             "خبرها چیه", "چه خبرا")):
        from universal_mind.self_status import self_status

        info = self_status()
        return _reflex_answer(c, info["report"])

    # R45-8 — THE WEEKLY LETTER, ASKED: «گزارش هفته چطور بود؟» reads the
    # letter the tick wrote (and if none is written yet, writes it NOW —
    # the answer is never a promise of a letter, it IS the letter).
    if "گزارش هفته" in c or "نامهی هفته" in c or ("گزارش" in c and "هفته" in c):
        from universal_mind.weekly_letter import latest_letter

        info = latest_letter()
        if not info.get("ok"):
            from universal_mind.weekly_letter import record_weekly_letter

            info = record_weekly_letter()
        return _reflex_answer(c, str(info.get("report", "")) or "نامهای نیست.")

    # «فایلهای ساختهشده امروز» — the artifacts of today's successes.
    if "فایل" in c and ("امروز" in c or "ساخته" in c or "درست کرده" in c):
        rows = _query(
            db,
            "SELECT command FROM run_history "
            "WHERE succeeded = 1 AND route != '' "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
            "AND date(created_at) = date('now', 'localtime') ORDER BY id DESC LIMIT 5",
        )
        if not rows:
            return _reflex_answer(c, "امروز فایلی ساخته نشده است.")
        names = [str(r["command"])[:30] for r in rows]
        return _reflex_answer(c, "کارهای موفق امروز: " + "؛ ".join(names) + ".")

    # «چند روز است زنده؟» — the REAL heartbeat history, not just "now".
    # (R44-13: the streak and the silent days, derived from the run store.)
    if (
        ("زنده" in c and ("چند" in c or "روز" in c or "است" in c))
        or ("تپش" in c and ("چند" in c or "وضع" in c or "چطور" in c or "چه" in c))
        or ("چند روزه" in c)
    ):
        from universal_mind.tick_pulse import pulse_report, pulse_sentence

        try:
            report = pulse_report(db=db)
        except Exception:  # noqa: BLE001 — a heartbeat answer never crashes
            return _reflex_answer(c, "نبضِ تپش را نتوانستم بخوانم.")
        return _reflex_answer(c, pulse_sentence(report))

    # «حافظهات چی میگن؟ / چی یاد گرفتی؟» — the REAL lessons, counted.
    if ("حافظه" in c or "یاد گرفتی" in c or "درس" in c) and (
        "میگن" in c or "گفته" in c or "چی" in c or "چه" in c or "یاد" in c
    ):
        try:
            rows = _query(db, "SELECT COUNT(*) AS n FROM planner_lessons")
            n = int(rows[0]["n"]) if rows else 0
            op_rows = _query(
                db,
                "SELECT operation, COUNT(*) AS n FROM planner_lessons "
                "GROUP BY operation ORDER BY n DESC LIMIT 3",
            )
            # R46-9 — TAUGHT WORDS too: the vocabulary the operator taught
            # («واژهی زرشک یعنی داده») is part of what the platform knows.
            vocab_rows: list[dict[str, Any]] = []
            try:
                from universal_mind.learned_vocab import learned_words

                vocab_rows = learned_words()
            except Exception:  # noqa: BLE001 — the learner is a lens
                vocab_rows = []
            vocab_part = ""
            if vocab_rows:
                vocab_part = " واژههای آموختهشده: " + "، ".join(
                    f"«{d['word']}»→{d['capability']}" for d in vocab_rows[:4]
                ) + "."
            if not op_rows and not vocab_rows:
                return _reflex_answer(c, "هنوز درسی یاد نگرفتهام — چند فرمان بده تا بیاموزم.")
            if not op_rows:
                return _reflex_answer(
                    c,
                    f"{_fa_num(len(vocab_rows))} واژه یاد گرفتهام." + vocab_part,
                )
            top = "، ".join(
                f"{r['operation']} ({_fa_num(int(r['n']))} بار)" for r in op_rows
            )
            return _reflex_answer(
                c,
                f"{_fa_num(n)} درس ثبت کردهام؛ پرتکرارترین عملیاتها: {top}." + vocab_part,
            )
        except Exception:  # noqa: BLE001 — a reflex never crashes
            return _reflex_answer(c, "هنوز درسی یاد نگرفتهام — چند فرمان بده تا بیاموزم.")

    return None


def _store() -> DatabaseSuite:
    """The shared persistent store (R42: ONE truth for every reader).

    Tolerant of a lambda-mocked class (test isolation): falls back to the
    constructor the lambda understands.
    """
    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


def state_fa(state: str) -> str:
    return {"done": "✅ تمام", "stopped": "⏸ متوقف", "active": "▶ فعال"}.get(state, state)


def _reflex_answer(command: str, answer: str) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "route": ["reflexive"],
        "matched_words": ["پرسش"],
        "unknown": [],
        "extracted_params": {},
        "result": {"reflexive": {"answer": answer}},
        "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
        "agent_report": answer,
    }


__all__ = ["answer_reflexive", "state_fa"]