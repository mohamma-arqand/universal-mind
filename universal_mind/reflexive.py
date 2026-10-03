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

    # R63 P4 — WINDOW ACTIONS: «پنجره‌های کروم را ببند». A measured dead
    # sentence: the platform could LIST windows but not act on them.
    # The close is GRACEFUL (CloseMainWindow — the app may save), every
    # closed window is NAMED, and a name matching nothing refuses with
    # the real open list (never a guessed process).
    if "ببند" in c and "پنجره" in c:
        import re as _re_w

        m_w = _re_w.search(r"پنجره‌?های\s+(.+?)\s+را\s+ببند", c) \
            or _re_w.search(r"پنجره\s+(.+?)\s+را\s+ببند", c)
        if m_w:
            from universal_mind.window_actions import close_by_name, close_fa

            res = close_by_name(m_w.group(1))
            return _reflex_answer(c, close_fa(res), ok=bool(res.get("ok")))

    # R63 P7 — TIME SINCE A REMEMBERED FACT: «چند ساعت از خواب من گذشته؟».
    # The platform cannot SEE the operator's sleep — but a fact they
    # TAUGHT it («یادت باشد که ساعت ۲۳ خوابیدم») has a timestamp, and the
    # elapsed time SINCE that fact is real arithmetic on real data.
    # Without a stored fact the answer is an honest refusal with the
    # exact way to make it answerable — never a guess about their life.
    if ("چند ساعت" in c or "چند وقت" in c) and "از" in c:
        import re as _re_since

        m_since = _re_since.search(
            r"چند\s+(?:ساعت|وقت)\s+از\s+(.+?)\s+(?:گذشته|گذشته|مضی)", c) \
            or _re_since.search(r"چند\s+(?:ساعت|وقت)\s+از\s+(.+?)[؟?]", c)
        if m_since:
            from datetime import datetime

            topic = m_since.group(1).strip().rstrip("؟?").strip()
            # «خواب من» -> «خواب»: the possessive is the operator's, not
            # the fact's words; keep the meaningful head only.
            topic = _re_since.sub(r"\s*من$", "", topic).strip() or topic
            db = DatabaseSuite.shared_persistent()
            q = db.query(
                "SELECT fact, created_at FROM named_memory "
                f"WHERE fact LIKE '%{topic.replace(chr(39), chr(39) * 2)}%' "
                "ORDER BY id DESC LIMIT 1")
            rows = q.get("rows", []) if q.get("ok") else []
            if not rows:
                # a one-shot REMINDER may carry the fact too (T1: a fact
                # with a moment becomes a reminder); since T5 every
                # scheduler run leaves its run_history row — THAT row's
                # timestamp is the registration moment.
                q2 = db.query(
                    "SELECT command, created_at FROM run_history "
                    f"WHERE command LIKE '%{topic.replace(chr(39), chr(39) * 2)}%' "
                    "ORDER BY id DESC LIMIT 1")
                rows = [
                    {"fact": r["command"], "created_at": r["created_at"]}
                    for r in (q2.get("rows", []) if q2.get("ok") else [])
                ]
            if rows:
                fact, stamp = rows[0]["fact"], str(rows[0]["created_at"] or "")
                try:
                    when = datetime.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S")
                    delta = datetime.now() - when
                    hours = delta.total_seconds() / 3600.0
                    if hours < 1:
                        amount = f"{int(delta.total_seconds() // 60)} دقیقه"
                    else:
                        amount = f"{hours:.1f} ساعت".replace(".", "٫")
                    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
                    return _reflex_answer(
                        c, f"از «{fact}» {amount.translate(fa)} گذشته است "
                           f"(ثبت: {stamp[:16]}).")
                except ValueError:
                    pass
            return _reflex_answer(
                c,
                f"خوابِ تو را نمی‌بینم — چیزی دربارهٔ «{topic}» یادم نیست. "
                "برای اینکه این پرسش جواب بگیرد، اول به من بگو: "
                "«یادت باشد که ساعت ۲۳ خوابیدم» — بعد «چند ساعت از خواب من گذشته؟» "
                "را دقیق جواب می‌دارم.",
                ok=False)

    # R65 P4 — THE CONTACT BOOK VIEW: «مخاطبهام را نشان بده» — the real
    # names the operator taught, never a fabrication.
    if "مخاطب" in c and any(w in c for w in ("نشان", "لیست", "فهرست", "چی", "چه", "کیه", "ها")):
        from universal_mind.contacts import list_contacts

        book = list_contacts()
        if not book:
            return _reflex_answer(
                c, "دفتر مخاطبینم خالی است — «آدرس ایمیل X را یادت باشد someone@example.com» یکی میسازد.")
        lines = [f"{_fa_num(len(book))} مخاطب دارم:"]
        for i, ct in enumerate(book[:10], 1):
            lines.append(f"  {_fa_num(i)}. {ct['name']} — {ct['address']}")
        if len(book) > 10:
            lines.append(f"  … و {_fa_num(len(book) - 10)} مورد دیگر")
        return _reflex_answer(c, "\n".join(lines))

    # R65 P5 — THE WEEKDAY FROM THE REAL CLOCK: «امروز چندشنبه است؟»
    if ("چندشنبه" in c or "چه روزی" in c) and ("امروز" in c or "امروزم" in c):
        from datetime import datetime

        # Python: Monday=0 … Sunday=6. The Persian week runs
        # شنبه(=Sat) یکشنبه(Sun) دوشنبه(Mon) … — index from Saturday:
        # Sat(py=5)->0, Sun(6)->1, Mon(0)->2, …  =>  (py + 2) % 7
        _DAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
        _py = datetime.now().weekday()
        today_fa = _DAYS[(_py + 2) % 7]
        tomorrow_fa = _DAYS[(_py + 3) % 7]
        return _reflex_answer(
            c, f"امروز {today_fa} است؛ فردا {tomorrow_fa}.")

    # R71 P4 — «۲۰ روز دیگر چندمه؟»: the date N DAYS FROM NOW (the sweep
    # caught it unrecognized — the delta reader only knew hours/minutes).
    import re as _re_r71

    _m_r71 = _re_r71.search(r"(\d+)\s*روز\s*(?:دیگر|بعد)", c)
    if _m_r71 is not None:
        from datetime import date as _date_r71, timedelta as _td_r71

        _n_days = int(_m_r71.group(1))
        _tgt_r71 = _date_r71.today() + _td_r71(days=_n_days)
        _fa_r71 = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        try:
            from jdatetime import date as _jdate_r71

            _j = _jdate_r71.fromgregorian(date=_tgt_r71)
            _months_r71 = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                           "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
            _txt_r71 = (f"{_n_days} روز دیگر "
                        f"{str(_j.day).translate(_fa_r71)} {_months_r71[_j.month - 1]} "
                        f"({str(_j.year).translate(_fa_r71)}) است.")
        except ImportError:
            _txt_r71 = (f"{_n_days} روز دیگر "
                        f"{_tgt_r71.strftime('%Y/%m/%d')} میلادی است.")
        return _reflex_answer(c, _txt_r71)

    # R66 P5 — THE NAMED DAY'S DATE: «شنبه چندم است؟» / «پنجشنبه هفته بعد
    # چندمه؟» — the operator names a weekday and asks for its DATE. The
    # answer comes from the real clock: the NEXT occurrence of that day
    # («هفته بعد» skips a full week further), rendered in Persian digits.
    import re as _re_day

    _m_day = _re_day.search(
        r"(شنبه|یکشنبه|دوشنبه|سه‌شنبه|سه شنبه|چهارشنبه|چهار شنبه|پنجشنبه|پنج شنبه|جمعه)"
        r"\s*(هفته بعد|هفته‌ی بعد|هفتهٔ بعد)?\s*(چندم|چندمه|چندم است|چندمه؟|چندم؟)", c)
    if _m_day is not None:
        from datetime import date as _date, timedelta as _timedelta

        _DAYS2 = {"شنبه": 5, "یکشنبه": 6, "دوشنبه": 0, "سه‌شنبه": 1, "سه شنبه": 1,
                  "چهارشنبه": 2, "چهار شنبه": 2, "پنجشنبه": 3, "پنج شنبه": 3, "جمعه": 4}
        _want = _DAYS2[_m_day.group(1)]
        _today = _date.today()
        _delta = (_want - _today.weekday()) % 7
        if _delta == 0:
            _delta = 7  # «شنبه» on a Saturday means the NEXT one
        if _m_day.group(2):  # «هفته بعد» — one full week further
            _delta += 7
        _target = _today + _timedelta(days=_delta)
        _fa_d = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        _months = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                   "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
        try:
            from jdatetime import date as _jdate

            _j = _jdate.fromgregorian(date=_target)
            _date_fa = (f"{str(_j.day).translate(_fa_d)} {_months[_j.month - 1]} "
                        f"({str(_j.year).translate(_fa_d)})")
        except ImportError:  # honest fallback: the Gregorian date, named
            _date_fa = (f"{str(_target.day).translate(_fa_d)}/"
                        f"{str(_target.month).translate(_fa_d)} میلادی")
        _rel = "هفته بعد" if _m_day.group(2) else ""
        return _reflex_answer(
            c, f"{_m_day.group(1)}{_rel and ' ' + _rel or ''} {_date_fa} است.")

    # R63 P6 — ENV VAR VIEW: «متغیر محیطی TEMP را نشان بده». The
    # operator's own environment, one named variable at a time. Secret-
    # looking names are masked (never printed), missing ones named.
    if "متغیر" in c and "محیط" in c and any(w in c for w in ("نشان", "بگو", "چیست", "چیه", "value")):
        import re as _re_env

        m_env = _re_env.search(r"متغیر\s*محیطی\s+([A-Za-z_][A-Za-z0-9_]*)", c)
        if m_env:
            from universal_mind.system_status_tool import SystemStatusTool

            res = SystemStatusTool().env_var(m_env.group(1))
            if res.get("ok"):
                answer = f"متغیر محیطی {res['name']} = {res['value']}"
            else:
                answer = str(res.get("error"))
            return _reflex_answer(c, answer, ok=bool(res.get("ok")))

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
        # R63 P5 — a RAM FLOOR in the question changes the answer's kind:
        # «کدام پروسه‌ها بیشتر از ۱ گیگ رم می‌خورند؟» is a FILTER, not a
        # generic top-5 — the old path answered something else entirely.
        import re as _re_ram

        m_ram = _re_ram.search(r"بیشتر\s+از\s+([\d۰-۹.,]+)\s*(گیگ|گیگابایت|مگ|مگابایت)", c)
        if m_ram and "رم" in c:
            from universal_mind.window_view import processes_by_ram, ram_filter_fa

            num = m_ram.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
            num = num.replace(",", ".")
            try:
                amount = float(num)
            except ValueError:
                amount = 0.0
            unit = m_ram.group(2)
            min_mb = amount * 1024.0 if unit.startswith("گیگ") else amount
            res = processes_by_ram(min_mb=min_mb)
            return _reflex_answer(c, ram_filter_fa(res, min_mb))
        from universal_mind.window_view import processes_fa, top_processes

        res = top_processes(5)
        return _reflex_answer(c, processes_fa(res))

    # R58 M4 — THE UPCOMING AGENDA: «برنامه‌ام را نشان بده» / «هفتهٔ بعد چی
    # کار دارم؟» — the sweep measured that no view exists of what is COMING.
    # The truth already lives in two tables: schedules (repeating + one-shot
    # reminders) and named_memory (notes that mention a time). Read-only,
    # sorted by when, Persian; empty is said honestly.

    # R62 T1 — «قرار» is the everyday word for the agenda (the review's
    # daily-user persona says «قرارهایم», not «برنامه‌ام»).
    # R63 P8 — «برنامه هفتهٔ آینده من چیست؟» also asks the agenda (the
    # sweep measured it falling to llm — the appointments are OUR data).
    _AGENDA_WORDS = ("برنامه‌ام", "برنامهام", "برنامهٔ من", "برنامه من",
                     "برنامه‌ی من", "برنامه هفته", "برنامهٔ هفته", "هفتهٔ بعد",
                     "هفته بعد", "هفتهٔ آینده", "هفته آینده",
                     "قرارهایم", "قرارهای من", "قرار‌هایم", "قرارام")
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
    # R70 P3 — «فردا چند تا قرار دارم؟» is a DAY-SCOPED count (the block
    # below would answer the blanket total). Let it fall through to the
    # day-scoped answer.
    if (("فردا" in c or "پس‌فردا" in c or "پس فردا" in c or "امشب" in c)
            and "قرار" in c and ("چند" in c or "چقدر" in c)):
        pass  # handled by the day-scoped block below
    elif "چند تا" in c or "چندتا" in c or "چند فرمان" in c or "چند تا فرمان" in c:
        # R64 P1 — THE QUESTION NAMES ITS OWN SUBJECT: a count of
        # REMINDERS is not a count of RUNS (the sweep caught «چند تا
        # یادآور دارم؟» answered with «۴۵۴۱۶ اجرا ثبت شده» — a real
        # number about the wrong thing is a lie). Each noun counts its
        # own table; an unknown noun asks for one.
        if "یادآور" in c or "یادآوری" in c or "قرار" in c or "reminder" in c.lower():
            rows = _query(db, "SELECT COUNT(*) AS n FROM schedules WHERE active = 1")
            n = int(rows[0]["n"]) if rows else 0
            if n == 0:
                return _reflex_answer(c, "هیچ یادآوری نداری — «یادم باشه …» یا «یادآور کن …» یکی میسازد.")
            return _reflex_answer(
                c, f"{_fa_num(n)} یادآور داری — «یادآورهای من» فهرستشان را نشان میدهد.")
        if "واژه" in c or "کلمه" in c and "یاد" in c:
            rows = _query(db, "SELECT COUNT(*) AS n FROM learned_vocab")
            n = int(rows[0]["n"]) if rows else 0
            if n == 0:
                return _reflex_answer(c, "هنوز هیچ واژهای از تو یاد نگرفتهام — «واژهی X یعنی Y» یکی میآموزد.")
            rows2 = _query(db, "SELECT word, capability FROM learned_vocab ORDER BY id DESC LIMIT 5")
            names = "، ".join(f"«{r['word']}»" for r in rows2) if rows2 else ""
            more = f" (تازه‌ها: {names})" if names else ""
            return _reflex_answer(c, f"{_fa_num(n)} واژه از تو یاد گرفتهام{more}.")
        if "فایل" in c or "پرونده" in c or "فایلی" in c:
            rows = _query(db, "SELECT COUNT(*) AS n FROM run_history WHERE route LIKE '%textfile%' AND succeeded = 1")
            n = int(rows[0]["n"]) if rows else 0
            if n == 0:
                return _reflex_answer(c, "هنوز هیچ فایلی نساختهام — «فایل X را بساز و داخلش بنویس Y» یکی میسازد.")
            return _reflex_answer(c, f"تا حالا {_fa_num(n)} بار فایل نوشتهام — «آخرین کارهایی که کردی» مسیرهایشان را نشان میدهد.")
        # R68 P2 — A CONTACT COUNT COUNTS THE CONTACT BOOK (the sweep caught
        # «چند تا مخاطب داری؟» answered with «۴۷۶۰۳ اجرا ثبت شده» — the run
        # count about the wrong noun; the same R64-P1 law, contact edition).
        if "مخاطب" in c or "مخاطبین" in c:
            rows = _query(db, "SELECT COUNT(*) AS n FROM contacts")
            n = int(rows[0]["n"]) if rows else 0
            if n == 0:
                return _reflex_answer(
                    c, "هنوز مخاطبی نداری — «آدرس ایمیل X را یادت باشد: a@b.com» یکی میسازد.")
            rows2 = _query(db, "SELECT name FROM contacts ORDER BY id DESC LIMIT 5")
            names = "، ".join(f"«{r['name']}»" for r in rows2) if rows2 else ""
            more = f" ({names})" if names else ""
            return _reflex_answer(
                c, f"{_fa_num(n)} مخاطب داری{more} — «مخاطبهام را نشان بده» فهرستشان را نشان میدهد.")
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

    # R70 P3 — «فردا چند تا قرار دارم؟»: the count of TOMORROW'S (or the
    # named day's) one-shots — not the blanket reminder count (the sweep
    # caught «فردا چند تا قرار دارم؟» answering with the TOTAL).
    # THE SUBSTRING LAW, SIXTH BITE: «پس‌فردا» CONTAINS «فردا» — the
    # longer word is tested FIRST or «پس‌فردا چند قرار» answers farda's
    # day (a live witness: the empty پس‌فردa answer listed farda's row).
    _day_words = None
    if "پس‌فردا" in c or "پس فردا" in c:
        _day_words = "پس‌فردا"
    elif "فردا" in c:
        _day_words = "فردا"
    elif "امشب" in c:
        _day_words = "امشب"
    if ("قرار" in c or "کار" in c and "دارم" in c) and "چند" in c and _day_words:
        from datetime import datetime as _dt70, timedelta as _td70

        _today70 = _dt70.now().date()
        _offset70 = {"فردا": 1, "پس‌فردا": 2, "امشب": 0}[_day_words]
        _target70 = _today70 + _td70(days=_offset70)
        _rows70 = _query(
            db,
            "SELECT command, run_at FROM schedules "
            "WHERE run_at != '' AND active = 1 ORDER BY run_at")
        _hits70 = []
        for r in _rows70:
            try:
                _fire70 = _dt70.fromisoformat(str(r["run_at"])).date()
            except ValueError:
                continue
            if _fire70 == _target70:
                _hits70.append(str(r["command"])[:40])
        if not _hits70:
            return _reflex_answer(
                c, f"{_day_words} هیچ قرارِ ثبت‌شده‌ای نداری — «یادم باشه {_day_words} ساعت …» یکی میسازد.")
        _fa_n70 = _fa_num(len(_hits70))
        _list70 = "؛ ".join(f"«{h}»" for h in _hits70[:5])
        return _reflex_answer(
            c, f"{_day_words} {_fa_n70} قرار داری: {_list70}.")

    # R70 P4 — «برنامه این هفته‌ام را نشان بده»: the WEEK'S real
    # appointments (one-shots within 7 days + the recurring ones, each
    # with its fire time), derived — never cached.
    if "برنامه" in c and ("هفته" in c or "این هفته" in c) and any(
            w in c for w in ("نشان", "بگو", "چی", "لیست")):
        from datetime import datetime as _dt71, timedelta as _td71

        _now71 = _dt71.now()
        _end71 = _now71 + _td71(days=7)
        _lines71 = []
        _rows71 = _query(
            db, "SELECT command, run_at, every_minutes, hour_of_day, active "
                "FROM schedules WHERE active = 1 ORDER BY run_at, id")
        for r in _rows71:
            _cmd71 = str(r["command"])[:40]
            if r["run_at"]:
                try:
                    _f71 = _dt71.fromisoformat(str(r["run_at"]))
                except ValueError:
                    continue
                if _now71 <= _f71 <= _end71:
                    _lines71.append(f"• {_f71.strftime('%m-%d %H:%M')} — «{_cmd71}»")
            elif r["every_minutes"]:
                _lines71.append(
                    f"• هر {str(r['every_minutes']).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))} دقیقه — «{_cmd71}»")
            elif r["hour_of_day"] and int(r["hour_of_day"]) >= 0:
                _h71 = str(r["hour_of_day"]).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                _lines71.append(f"• هر روز ساعت {_h71}:۰۰ — «{_cmd71}»")
        if not _lines71:
            return _reflex_answer(
                c, "هفتهٔ پیش رو هیچ برنامهٔ ثبت‌شده‌ای نداری — «یادم باشه …» یکی میسازد.")
        return _reflex_answer(c, "برنامهٔ این هفته:\n" + "\n".join(_lines71[:12]))

    # R70 P5 — «چه کارهای ناتمامی دارم؟»: the honest UNFINISHED list —
    # goals still active/stopped (never archived) plus one-shots still
    # ahead, each named with its state; empty is said plainly.
    if ("ناتمام" in c or "نیمه‌کاره" in c or "نیمه کاره" in c) and any(
            w in c for w in ("چی", "چه", "دارم", "داری", "نشان", "لیست")):
        # R70 P5 — UNFINISHED means active/stopped only: a DONE goal is
        # finished (the first draft listed done rows under «ناتمام» — a
        # live wrong answer about the operator's own state).
        _rows72 = _query(
            db, "SELECT goal, state FROM goals "
                "WHERE state IN ('active', 'stopped') "
                "ORDER BY id DESC LIMIT 10")
        _pend72 = _query(
            db, "SELECT command, run_at FROM schedules "
                "WHERE run_at != '' AND active = 1 ORDER BY run_at LIMIT 5")
        _out72 = []
        for r in _rows72:
            _st72 = {"active": "▶ در جریان", "stopped": "⏸ متوقف"}.get(
                str(r["state"]), str(r["state"]))
            _out72.append(f"• هدف «{str(r['goal'])[:50]}» — {_st72}")

        for r in _pend72:
            _due73 = str(r["run_at"])[:16]
            _out72.append(f"• قرار «{str(r['command'])[:40]}» — سرِ {_due73}")
        if not _out72:
            return _reflex_answer(c, "هیچ کارِ ناتمامی نداری — همه بسته شده‌اند.")
        return _reflex_answer(c, "کارهای ناتمام:\n" + "\n".join(_out72[:10]))

    # R68 P3 — «وضعیت کلی من چطور است؟»: the DAY REVIEW. The operator
    # asks about THEMSELVES (today's real activity), not the goal board —
    # the sweep caught it answering with old scheduled goals. Real counts
    # from run_history (today), the day's top routes, and the last command.
    if ("وضعیت کلی" in c or "وضعیت روز" in c) and ("من" in c or "امروز" in c or "چطور" in c):
        from datetime import datetime as _dt

        _today = _dt.now().strftime("%Y-%m-%d")
        tot = _query(db, f"SELECT COUNT(*) AS n FROM run_history WHERE date(created_at) = '{_today}'")
        okc = _query(db, f"SELECT COUNT(*) AS n FROM run_history WHERE date(created_at) = '{_today}' AND succeeded = 1")
        n_tot = int(tot[0]["n"]) if tot else 0
        n_ok = int(okc[0]["n"]) if okc else 0
        top = _query(
            db,
            f"SELECT route, COUNT(*) AS n FROM run_history "
            f"WHERE date(created_at) = '{_today}' AND succeeded = 1 AND route != '' "
            f"GROUP BY route ORDER BY n DESC LIMIT 3")
        last = _query(
            db, "SELECT command FROM run_history ORDER BY id DESC LIMIT 1")
        _pct = round(100 * n_ok / n_tot) if n_tot else 0
        if n_tot == 0:
            return _reflex_answer(c, "امروز هنوز کاری برایت انجام ندادهام.")
        _tops = "، ".join(f"{r['route']} ({_fa_num(r['n'])} بار)" for r in top) if top else ""
        _last_cmd = str(last[0]["command"])[:40] if last else ""
        return _reflex_answer(
            c,
            f"وضعیت امروز: {_fa_num(n_tot)} فرمان اجرا کردم؛ {_fa_num(n_ok)} موفق ({_fa_num(_pct)}٪)."
            + (f" بیشتر در: {_tops}." if _tops else ".")
            + (f" آخرین فرمان: «{_last_cmd}»." if _last_cmd else ""),
        )

    # R68 P4 — «چه مدت است روشن نیستم؟» / «آخرین بار کی بود؟»: the SINCE-
    # LAST-ACTIVITY answer from the real clock (the gap between the last
    # recorded run and now — an honest «من همیشه آمادهام» for an empty
    # or just-now history).
    if ("چه مدت" in c or "چقدر وقته" in c or "از کی" in c) and ("روشن" in c or "کار" in c or "بیدار" in c):
        from datetime import datetime as _dt2

        rows = _query(db, "SELECT created_at FROM run_history ORDER BY id DESC LIMIT 1")
        if not rows:
            return _reflex_answer(c, "هنوز چیزی ثبت نشده — الان شروع میکنم.")
        _last_t = str(rows[0]["created_at"])
        try:
            _lt = _dt2.strptime(_last_t[:19], "%Y-%m-%d %H:%M:%S")
            _gap = (_dt2.now() - _lt).total_seconds()
        except ValueError:
            return _reflex_answer(c, "زمان آخرین فعالیت را نخواندم — ولی الان بیدارم.")
        if _gap < 60:
            return _reflex_answer(c, f"همین حالا با هم کار میکنیم ({_fa_num(int(_gap))} ثانیه پیش).")
        if _gap < 3600:
            return _reflex_answer(c, f"{_fa_num(int(_gap // 60))} دقیقه از آخرین کارمان گذشته.")
        if _gap < 86400:
            _hh, _mm = divmod(int(_gap // 3600), 1), int((_gap % 3600) // 60)
            return _reflex_answer(c, f"{_fa_num(int(_gap // 3600))} ساعت و {_fa_num(_mm)} دقیقه از آخرین کارمان گذشته.")
        return _reflex_answer(c, f"{_fa_num(int(_gap // 86400))} روز از آخرین کارمان گذشته — دوباره بیدارم.")

    # R68 P5 — «چه چیزهایی بلد نیستی؟»: THE HONEST CONFESSION. The
    # capability registry is read live (what IS there), and the standing
    # gaps are named plainly (llm knowledge needs a live model; live
    # weather/web needs a network; anything unsaid is a «نمیدانم»).
    if ("بلد نیستی" in c or "نمیتوانی" in c or "نمی‌توانی" in c) and "چی" in c:
        _REG = (
            "چیزهایی که نمیتوانم: (۱) پرسشهای دانشیِ عمومی — پاسخشان به یک "
            "مدل زبانی زنده نیاز دارد و الان وصل نیستم؛ جواب حدسی نمیدهم. "
            "(۲) هوای همین حالا و هر دادهی بیرونیِ زنده — منبع زنده ندارم؛ "
            "صادقانه میگویم و راه درست را نشان میدهم. (۳) هر کاری که در "
            "قابلیتهایم نیست، همان لحاظ «نمیدانم» میگیرد — نه جواب ساختگی."
        )
        return _reflex_answer(c, _REG)

    # R68 P6 — «آخرین خطای من چه بود؟»: the LAST FAILED RUN, real from
    # run_history — what failed and why it failed (the honest post-mortem).
    if ("آخرین خطا" in c or "آخرین اشتباه" in c) and ("چی" in c or "چه" in c or "بود" in c):
        rows = _query(
            db, "SELECT command, route, created_at FROM run_history "
                "WHERE succeeded = 0 ORDER BY id DESC LIMIT 1")
        if not rows:
            return _reflex_answer(c, "هیچ خطای ثبت‌شدهای ندارم — همهی رانها موفق بودهاند.")
        r0 = rows[0]
        return _reflex_answer(
            c,
            f"آخرین خطا: «{str(r0['command'])[:50]}» (مسیر {r0['route'] or 'نامشخص'}) "
            f"در {str(r0['created_at'])[:19]} ناموفق بود. «چرا شکست خورد؟» علتش را میپرسم.",
        )

    # R68 P7 — «مصرف امروزم چطور بوده؟»: today's per-route consumption —
    # the real count per capability for TODAY only (not the all-time wall).
    if "مصرف" in c and ("امروز" in c or "امروزم" in c):
        from datetime import datetime as _dt3

        _today3 = _dt3.now().strftime("%Y-%m-%d")
        rows = _query(
            db,
            f"SELECT route, COUNT(*) AS n FROM run_history "
            f"WHERE date(created_at) = '{_today3}' AND succeeded = 1 AND route != '' "
            f"GROUP BY route ORDER BY n DESC LIMIT 8")
        if not rows:
            return _reflex_answer(c, "امروز هنوز فرمانی اجرا نشده.")
        _parts = "، ".join(f"{r['route']}: {_fa_num(r['n'])}" for r in rows)
        _tot = sum(int(r["n"]) for r in rows)
        return _reflex_answer(c, f"مصرف امروز ({_fa_num(_tot)} ران موفق): {_parts}.")

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

        # R67 P7 — «چند دقیقه تا ساعت ۲۰ مانده؟»: the NAMED hour. The
        # answer is the real distance on the 24h clock (a past hour today
        # means TOMORROW's occurrence — time only moves forward).
        import re as _re_hm

        _m_named = _re_hm.search(r"تا\s+ساعت\s+([۰-۹0-9]{1,2})", c)
        if _m_named is not None and "بعد" not in c:
            _want = int(_m_named.group(1).translate(
                str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
            if 0 <= _want <= 23:
                _tgt = _now.replace(hour=_want, minute=0, second=0, microsecond=0)
                if _tgt <= _now:
                    _tgt += timedelta(days=1)  # today's slot passed → tomorrow
                _mins2 = int((_tgt - _now).total_seconds() // 60)
                _h2, _m2 = divmod(_mins2, 60)
                if _h2 > 0:
                    _txt2 = (f"تا ساعت {_fa_num(_want)}، {_fa_num(_h2)} ساعت "
                             f"و {_fa_num(_m2)} دقیقه مانده")
                else:
                    _txt2 = f"تا ساعت {_fa_num(_want)}، {_fa_num(_mins2)} دقیقه مانده"
                return _reflex_answer(c, _txt2 + ".")

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

    # R62 T2 — KNOWLEDGE QUESTIONS WITHOUT DATA: «هوا تهران چطوره؟» /
    # «قیمت طلا چنده؟» / «اخبار امروز چیست؟» ask the WORLD, and the world
    # is not in this machine. The honest answer names the gap and gives
    # BOTH real roads: a live model (if wired) or fetching a page —
    # never «نشناختم» (the sentence IS understood; the data is what is
    # missing) and never a fabricated number.
    # NOTE: «خبر چیست؟» in everyday speech asks the PLATFORM's own state
    # (the five-signal answer), not world news — only the explicit
    # «اخبار» is a world-data topic (a live test caught the collision).
    _KNOW_TOPICS = ("هوا", "دمای هوا", "قیمت", "نرخ", "اخبار",
                    "ارز", "دلار", "طلا", "سکه", "بورس", "تورم")
    _KNOW_ASK = ("چطوره", "چطور است", "چیه", "چیست", "چنده", "چند است", "کیه", "چی شده")
    if any(t in c for t in _KNOW_TOPICS) and any(a in c for a in _KNOW_ASK):
        topic = next(t for t in _KNOW_TOPICS if t in c)
        # the promise is real: the question is HARVESTED so the first live
        # connection can answer it (the same ledger the LLM path uses).
        try:
            from universal_mind.unknown_harvest import harvest_unknown

            harvest_unknown([c])
        except Exception:  # noqa: BLE001 — harvesting never blocks the answer
            pass
        return _reflex_answer(
            c,
            f"پرسشِ «{topic}» دادهٔ بیرونی می‌خواهد و من به منبعِ زنده وصل نیستم — "
            "جوابِ حدسی نمی‌سازم.\n"
            "دو راهِ واقعی: (۱) اگر مدلِ زنده وصل است، همین را با «هوش مصنوعی» بپرس؛ "
            "(۲) «سایت [آدرس] را بخوان» تا دادهٔ واقعی را برایت بیاورم و خلاصه کنم.\n"
            "پرسشت را در فهرستِ ناشناخته‌ها ثبت کردم تا با اولین اتصال، جوابش را بگیرم.",
        )

    # R62 T5 — CANCEL/UNDO: «لغو کن» / «برگرد عقب» / «آخرین کار را پاک کن».
    # An automatic universal undo would be a lie (a fired reminder, a
    # written file, a spoken word — each unwinds differently). The honest
    # answer names WHAT the last run did (from the real history) and
    # teaches the exact per-effect remedy; never a fake "باطل شد".
    # R64 P2 — the spoken PREFIXES carry the same intent: «اشتباه شد،
    # لغو کن» / «نه، لغو کن» / «برگرد عقب دیگه» (the sweep caught the
    # bare-form-only gate refusing them).
    _c_stripped = c.strip().rstrip(".،؛!")
    _cancel_bare = _c_stripped in (
        "لغو کن", "برگرد عقب", "آخرین کار را پاک کن", "کنسل کن", "undo", "برگردون")
    _cancel_prefix = any(
        _c_stripped.endswith(w) for w in
        ("لغو کن", "لغو", "کنسل کن", "کنسل", "برگرد عقب", "برگردون", "undo"))
    if _cancel_bare or _cancel_prefix or c.startswith("لغو"):
        db = DatabaseSuite.shared_persistent()
        q = db.query(
            "SELECT id, command, route, succeeded FROM run_history "
            "ORDER BY id DESC LIMIT 5"
        )
        rows = q.get("rows", []) if q.get("ok") else []
        _CANCEL_SHAPES = ("لغو کن", "لغو کن.", "برگرد عقب", "آخرین کار را پاک کن",
                          "کنسل کن", "برگردون", "undo")
        last = next((r for r in rows if str(r["command"]).strip().rstrip(".،؛!")
                     not in _CANCEL_SHAPES), None)
        if last is None:
            return _reflex_answer(c, "کاری که بتوانم لغو کنم پیدا نکردم — هنوز چیزی اجرا نکردهام.")
        cmd_fa = str(last["command"])[:40]
        route = str(last["route"] or "")
        if "scheduler" in route or "یادآور" in str(last["command"]):
            remedy = "یادآورها با «یادآوری N را حذف کن» پاک می‌شوند — «یادآورهای من» شماره‌ها را نشان می‌دهد."
        elif "textfile" in route:
            remedy = "فایل نوشته‌شده را خودت پاک کن (من بدون «تأیید کن» چیزی حذف نمی‌کنم) — مسیرش در همان گزارش بود."
        elif "chart" in route or "pdf" in route:
            remedy = "خروجی در پوشهٔ موقت ساخته شد؛ اگر مسیرش را از گزارش برداشتی، همان را می‌توانی پاک کنی."
        else:
            remedy = "این اجرا اثرِ برگشت‌پذیرِ خودکار ندارد — اگر فایل/یادآور ساخته، راهِ همان را جداگانه بگو."
        return _reflex_answer(
            c,
            f"لغوِ خودکار نمی‌کنم — اثرِ هر اجرا راهِ برگشتِ خودش را دارد.\n"
            f"آخرین کار: «{cmd_fa}». {remedy}",
        )

    # R62 T4 — SPEECH ACCESSIBILITY: «کندتر/سریع‌تر حرف بزن» changes the
    # REMEMBERED SAPI rate (−10..+10) — the next «بلند بخوان» speaks at
    # the operator's pace, and the answer states the new value and the
    # way back. The setting is a PREFERENCE (persisted, applied at run),
    # never a per-call guess.
    if ("حرف بزن" in c or "بگو" in c or "صحبت کن" in c or "بلند بخوان" in c) and (
        "کندتر" in c or "کند تر" in c or "آهسته‌تر" in c or "آهسته تر" in c
        or "سریع‌تر" in c or "سریع تر" in c or "آرام‌تر" in c or "آرام تر" in c
    ):
        from universal_mind import operator_preferences as _op

        current = int(_op.get("speech_rate") or 0)
        if "کندتر" in c or "آهسته" in c or "آرام" in c:
            new_rate = max(-10, current - 2)
            word = "کندتر"
        else:
            new_rate = min(10, current + 2)
            word = "سریع‌تر"
        _op.set("speech_rate", str(new_rate))
        return _reflex_answer(
            c,
            f"سرعت گفتارم را {word} کردم ({_fa_num(new_rate)} در مقیاس −۱۰ تا ۱۰) — "
            "از این به بعد «بلند بخوان» با همین سرعت حرف می‌زند. "
            "«سریع‌تر حرف بزن» یا «کندتر حرف بزن» هر وقت خواستی تنظیمش می‌کند.",
        )

    # «چند وقته دستگاه روشن است؟» — the REAL Windows uptime (WMI), honest.
    if ("دستگاه" in c or "سیستم" in c or "کامپیوتر" in c) and (
        "روشن" in c and ("چند" in c or "وقت" in c or "مدت" in c)
    ):
        return _reflex_answer(c, _windows_uptime_fa())

    # «راهنما / چیکار میتونی بکنی؟ / چی بلدی؟ / قابلیتهات» — the list, counted.
    if (
        c in ("راهنما", "help", "کمک", "کمک!", "کمم")
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


def _reflex_answer(command: str, answer: str, *, ok: bool = True) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "route": ["reflexive"],
        "matched_words": ["پرسش"],
        "unknown": [],
        "extracted_params": {},
        "result": {"reflexive": {"answer": answer}},
        "errors": {} if ok else {"reflexive": answer[:80]},
        "durations_ms": {}, "flows": [], "judgment": {},
        "agent_report": answer,
    }


__all__ = ["answer_reflexive", "state_fa"]