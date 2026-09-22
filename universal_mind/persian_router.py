"""Persian natural-language router — فارسی بگو، سیستم خودش اجرا کند.

The bridge between a Persian-speaking operator and the 87-operation super-platform:
a command like «میانگین این اعداد را حساب کن و نمودارش کن» is mapped to the
capability chain (data → chart) and executed through the same orchestrate engine
every other door uses.

This is a deterministic keyword router over declared vocabulary — NOT an LLM. Every
mapping is explicit and testable: a given Persian phrase always routes to the same
chain. Unknown words are reported honestly (never a guessed chain).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.tool_registry import ToolRegistry


@dataclass(frozen=True)
class PersianRoute:
    """The learned/derived plan for one Persian command."""

    command: str
    capabilities: tuple[str, ...]   # execution order
    matched_words: tuple[str, ...]  # which Persian words triggered each capability
    unknown: tuple[str, ...]        # Persian words that matched nothing (honest)

    @property
    def ok(self) -> bool:
        return bool(self.capabilities)


# Persian vocabulary → capability. One phrase can trigger several capabilities
# (e.g. «نمودار» → chart, «ذخیره» → database), and chains are built from what fires.
_VOCAB: tuple[tuple[str, str], ...] = (
    # data (numpy) — formal AND colloquial forms
    ("میانگین", "data"),
    ("میانگینشو", "data"),
    ("میانگینش", "data"),
    ("میانگین بگیر", "data"),
    ("میانگین بگیره", "data"),
    ("حسابش کن", "data"),
    ("حساب کن", "data"),
    ("میانگین ", "data"),
    ("انحراف", "data"),
    ("آمار", "data"),
    ("محاسبه", "data"),
    ("همبستگی", "data"),
    ("معادله", "data"),
    ("درصد", "data"),
    ("ضرب", "data"),
    ("تقسیم", "data"),
    ("جذر", "data"),
    ("مدیان", "data"),
    ("میانه", "data"),
    ("توان", "data"),
    ("تبدیل", "data"),
    ("نرمال", "data"),
    ("ماتریس", "data"),
    # chart (matplotlib) — formal AND colloquial
    ("نمودار", "chart"),
    ("نمودارشو", "chart"),
    ("نمودارش", "chart"),
    ("نمودار بکش", "chart"),
    ("بکش", "chart"),
    ("رسم", "chart"),
    ("رسمش کن", "chart"),
    ("خطی", "chart"),
    ("میله", "chart"),
    ("دایره", "chart"),
    ("هیستوگرام", "chart"),
    ("پراکنده", "chart"),
    # pdf (reportlab)
    ("پی دی اف", "pdf"),
    ("پی‌دی‌اف", "pdf"),
    ("pdf", "pdf"),
    ("فایل pdf", "pdf"),
    ("گزارش", "pdf"),
    ("سند", "pdf"),
    ("فاکتور", "pdf"),
    ("جدول در سند", "pdf"),
    # image (Pillow)
    ("تصویر", "image"),
    ("عکس", "image"),
    ("تغییر اندازه", "image"),
    ("برش", "image"),
    ("چرخش", "image"),
    ("فیلتر تصویر", "image"),
    ("سیاه سفید", "image"),
    ("واترمارک", "image"),
    # database (SQLite) — formal AND colloquial
    ("ذخیره", "database"),
    ("ذخیرهش کن", "database"),
    ("ذخیره کن", "database"),
    ("دیتابیس", "database"),
    ("جدول", "database"),
    ("کوئری", "database"),
    ("پرس‌وجو", "database"),
    # media (ffmpeg)
    ("ویدیو", "media"),
    ("رسانه", "media"),
    ("فیلم", "media"),
    ("تبدیل ویدیو", "media"),
    # archive (gzip)
    ("فشرده", "archive"),
    ("زیپ کن", "archive"),
    ("تحلیل کن", "data"),
    ("تحلیل بده", "data"),
    ("آنالیز", "data"),
    ("رابطه بین", "data"),
    ("آرشیو", "archive"),
    ("بایگانی", "archive"),
    ("بایگانیش کن", "archive"),
    # vision (OpenCV) — تحلیل تصویر واقعی
    ("بینایی", "vision"),
    ("تحلیل تصویر", "vision"),
    ("این صفحه را ببین", "vision"),
    ("ببین و بگو", "vision"),
    ("ساختارش را بخوان", "vision"),
    ("ساختار تصویر", "vision"),
    ("ساختارش", "vision"),
    # webfetch (urllib) — the platform reaches the web
    ("وب را بگیر", "webfetch"),
    ("صفحه وب", "webfetch"),
    ("سایت", "webfetch"),
    ("آدرسش را بگیر", "webfetch"),
    ("لینک", "webfetch"),
    ("باز کن", "webfetch"),
    # screenshot (ImageGrab) — the platform captures the screen
    ("اسکرینشات", "screenshot"),
    ("از صفحه عکس بگیر", "screenshot"),
    ("صفحه را بگیر", "screenshot"),
    # pdfreader (pypdf) — the platform reads PDFs
    ("متن پی دی اف", "pdfreader"),
    ("pdf را بخوان", "pdfreader"),
    ("پی دی افش را بخوان", "pdfreader"),
    # == واژههای روزمرهی نزدیک به قابلیتهای موجود (نه قابلیت جدید — نقش) ==
    # چاپ/پرینت → سند (pdf)؛ ترجمه → گرفتن وب + سند؛ جستجو/شبکه → وب؛
    # تقویم/زمان → داده؛ یادداشت → کلیپبورد؛ دانلود/اسکن/آپلود → وب؛ هشدار → اعلان
    ("چاپ کن", "pdf"),
    ("پرینت", "pdf"),
    ("ترجمه", "webfetch"),
    ("جستجو", "webfetch"),
    ("سرچ", "webfetch"),
    ("تقویم", "data"),
    ("یادداشت", "clipboard"),
    ("نوت کن", "clipboard"),
    ("دانلود", "webfetch"),
    ("اسکن", "image"),
    ("آپلود", "webfetch"),
    ("هشدار", "notify"),
    ("یادآوری کن", "notify"),
    ("زمان بگیر", "notify"),
    ("یادم بندی", "notify"),
    ("یادم بیاور", "notify"),
    ("شبکه", "webfetch"),

    # zip (stdlib) — the world's archive format
    ("زیپش کن", "zip"),
    ("در زیپ", "zip"),
    ("بستهبندی کن", "zip"),
    # csv (stdlib) — the universal interchange
    ("در سیاسوی", "csv"),
    ("سیاسویش کن", "csv"),
    ("csv کن", "csv"),
    # excel (openpyxl) — real spreadsheets
    ("اکسل", "excel"),
    ("در اکسل", "excel"),
    ("صفحهگسترده", "excel"),
    # ocr (Windows.Media.Ocr) — the platform READS images
    ("متنش را بخوان", "ocr"),
    ("متن تصویر", "ocr"),
    ("ocr کن", "ocr"),
    # speech (SAPI) — the platform speaks its results aloud
    ("بگو", "speech"),
    ("بلند بخوان", "speech"),
    ("گوش کن", "speech"),
    ("صدا", "speech"),
    ("بخوان بلند", "speech"),
    ("با صدا", "speech"),
    ("صدا کن", "speech"),
    # media (ffmpeg) — PLAYING a real audio/video file is media, not speech
    ("موسیقی", "media"),
    ("پخش کن", "media"),
    ("فایل صوتی", "media"),
    ("فایل ویدیو", "media"),
    # متن بنویس = a durable TEXT artifact (a written document), not the clipboard
    ("متن بنویس", "pdf"),

    # گزارش کامل: the EVERYTHING chain — numbers → chart → report → archive
    ("گزارش کامل", "data"),
    ("گزارش کامل", "chart"),
    ("گزارش کامل", "pdf"),
    ("گزارش کامل", "archive"),
    ("لبه", "vision"),
    ("لبهها", "vision"),
    ("کنتور", "vision"),
    ("خطوط تصویر", "vision"),
    ("تشخیص لبه", "vision"),
    ("پردازش تصویر", "vision"),
    # ai (sklearn/scipy) — یادگیری ماشین واقعی
    ("یادگیری", "ai"),
    ("یادگیری ماشین", "ai"),
    ("خوشه", "ai"),
    ("خوشهبندی", "ai"),
    ("خوشه بندی", "ai"),
    ("طبقهبندی", "ai"),
    ("طبقه بندی", "ai"),
    ("رگرسیون", "ai"),
    ("مدل", "ai"),
    ("آموزش", "ai"),
    ("فوریه", "ai"),
    ("سیگنال", "ai"),
    ("پیشبینی", "ai"),
    ("پیش بینی", "ai"),
    # saved chains — «زنجیرهی X را اجرا کن» runs the operator's saved chain
    ("زنجیره", "chain"),
    ("زنجیرهی", "chain"),
    # compute (node)
    ("جاوااسکریپت", "compute"),
    ("جاوا اسکریپت", "compute"),
    ("نود", "compute"),
    # notify (Windows toast)
    ("اطلاع بده", "notify"),
    ("اعلان", "notify"),
    ("پیام بده", "notify"),
    ("یادآوری کن", "notify"),
    # clipboard
    ("کلیپبورد", "clipboard"),
    ("بفرست", "clipboard"),
    ("بنویس", "clipboard"),
    ("تایپ کن", "clipboard"),
    ("کپی کن", "clipboard"),
    ("بفرست به کلیپبورد", "clipboard"),
)

# Ordering preference: which capability should run FIRST when several fire.
# data/compute produce inputs; chart/pdf consume them; database/notify/archive
# are sinks. The order below is the natural data-flow order.
_PRIORITY: tuple[str, ...] = (
    "data", "compute", "image", "media", "vision", "ai",
    "chart", "pdf", "database", "archive", "clipboard", "notify",
)
# "chain" is a dispatch word, never an executable capability: when other words
# also fire, the chain pseudo-capability is dropped so the real ones run.
_NON_EXECUTABLE = {"chain"}


def _resolve_saved_chain(command: str) -> tuple[str, ...] | None:
    """Find the operator's saved chain whose name appears in the command.

    «زنجیرهی گزارش هفتگی را اجرا کن» matches a saved chain named «گزارش هفتگی».
    Returns the chain's capabilities, or None when no saved chain name matches —
    never a guessed chain.
    """
    try:
        from universal_mind.chains_store import ChainsStore
    except Exception:  # noqa: BLE001 — a missing store never breaks routing
        return None
    try:
        saved = ChainsStore().load()
    except Exception:  # noqa: BLE001
        return None
    lowered = command.lower()
    # Longest name first, so a longer saved name wins over a shorter prefix.
    for chain in sorted(saved, key=lambda c: -len(c.name)):
        if chain.name in lowered:
            return chain.capabilities
    return None


def route(command: str) -> PersianRoute:
    """Map a Persian command to a capability chain (deterministic, honest)."""
    lowered = command.lower()
    matched: dict[str, list[str]] = {}

    for word, capability in _VOCAB:
        if word in lowered:
            matched.setdefault(capability, []).append(word)

    if "chain" in matched and not any(c for c in matched if c != "chain"):
        # A pure chain command («زنجیرهی X را اجرا کن») — the route is resolved
        # from the operator's SAVED chains, not from the capability vocabulary.
        saved = _resolve_saved_chain(command)
        if saved is not None:
            return PersianRoute(
                command=command,
                capabilities=saved,
                matched_words=("زنجیره",),
                unknown=(),
            )
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))

    # Intent disambiguation: «تحلیل تصویر...» means ANALYZE (vision), not
    # make/edit (image) — the bare «تصویر» (an image-production word) must not
    # fire when the analysis phrase is present in the same sentence.
    analysis_intent = any(
        w in lowered for w in ("تحلیل تصویر", "پردازش تصویر", "بینایی ماشین", "متن تصویر", "متنش را بخوان")
    )
    if analysis_intent:
        matched.pop("image", None)

    # «متن بنویس» = WRITE a text document (pdf) — the explicit intent wins
    # over the bare «بنویس» (clipboard paste). Explicit > inference, always.
    if "متن بنویس" in lowered:
        matched.pop("clipboard", None)

    if not matched:
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))

    # Order capabilities by the natural data-flow priority; ties keep first-seen.
    executable = [c for c in matched if c not in _NON_EXECUTABLE]
    if not executable:
        # A pure «زنجیره...» command (handled above) or nothing executable.
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))
    caps = sorted(
        executable,
        key=lambda c: (_PRIORITY.index(c) if c in _PRIORITY else len(_PRIORITY), executable.index(c)),
    )
    words = tuple(w for c in caps for w in matched[c])

    # Honest unknowns: Persian words present in the command that matched nothing.
    import re

    tokens = [w for w in re.split(r"[\s،.,؛!؟]+", command) if w.strip()]
    known_flat = {w for w, _ in _VOCAB}
    unknown: list[str] = [t for t in tokens if t not in known_flat and not t.replace(".", "").isdigit()]

    return PersianRoute(
        command=command,
        capabilities=tuple(caps),
        matched_words=words,
        unknown=tuple(unknown),
    )


def route_and_run(
    command: str,
    registry: ToolRegistry | None = None,
    *,
    params: dict[str, Any] | None = None,
    forced_route: list[str] | None = None,
    explain_only: bool = False,
) -> dict[str, Any]:
    """Route a Persian command AND execute the resulting chain for real.

    A GOAL sentence («هدف: ...») is routed to the AGENT layer instead: the
    steps are parsed, run under ARETĒ judgment, and the result carries the
    agent's report (the goal loop with its verdicts). Ordinary commands are
    never hijacked — the goal marker is explicit intent.
    """
    # R44-1 — «توضیح بده» / «فقط بگو چه میکنی»: the EXPLAIN marker strips
    # itself from the command and runs the plan EXPLAINED, never executed.
    # It precedes every route (even reflexive — «توضیح بده» means the NEXT
    # real work's plan, and it composes: «نمودار بکش و گزارشش کن — توضیح بده»).
    _explain = explain_only
    _work_command = command
    if forced_route is None:
        for marker in ("توضیح بده", "فقط بگو چه میکنی", "فقط بگو چه کار میکنی"):
            if marker in command:
                _explain = True
                _work_command = command.replace(marker, "").replace("  — ", "").replace(" — ", "").strip()
                break
    explain_only = _explain

    # THE REFLEXIVE CLASS — self-questions answered from the REAL store
    # (never a capability run, never a guess). The marker is a question
    # about the platform itself, and it precedes every other route.
    if forced_route is None:
        from universal_mind.reflexive import answer_reflexive

        reflex = answer_reflexive(command)
        if reflex is not None:
            return {
                **reflex,
                "_registry": registry or ToolRegistry(),
            }

    # R44-3 — THE OPERATOR'S VERDICT: «عالی بود» / «بد بود» after a run is
    # the HUMAN JUDGE speaking. It binds to the last real run of the
    # previous command and re-weights future route selection. It precedes
    # every executable route — a verdict is never a capability run.
    if forced_route is None:
        from universal_mind.operator_verdicts import is_verdict_phrase, record_verdict

        if is_verdict_phrase(command):
            # bind to the LAST REAL SUCCESSFUL run in the store — the operator
            # rules on the work the platform just did, whatever it was.
            try:
                _last = _status_store().query(
                    "SELECT command FROM run_history WHERE succeeded = 1 "
                    "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
                    "ORDER BY id DESC LIMIT 1"
                ).get("rows", [])
                _target = str(_last[0]["command"]) if _last else ""
            except Exception:  # noqa: BLE001 — a verdict never crashes
                _target = ""
            out = record_verdict(_target, "good" if "بد" not in command else "bad")
            return {
                "ok": out.get("ok", False),
                "command": command,
                "route": ["verdict"],
                "matched_words": ["رأی"],
                "unknown": [],
                "extracted_params": {},
                "result": {"verdict": out},
                "errors": {},
                "durations_ms": {},
                "flows": [],
                "judgment": {},
                "agent_report": str(out.get("answer", "رأیت ثبت شد.")),
                "_registry": registry or ToolRegistry(),
            }

    # THE CONVERSATIONAL CLASS — small talk gets a warm SHORT answer, never
    # silence. «سلام» answering with a hole is a broken first impression.
    if forced_route is None:
        from universal_mind.conversational import answer_conversational

        chat = answer_conversational(command)
        if chat is not None:
            return {
                **chat,
                "_registry": registry or ToolRegistry(),
            }

    # CONVERSATION MEMORY — «و حالا نمودارش را بکش» speaks of the LAST run.
    # The rule: a command whose ONLY subject is the anaphora («نمودارش» — the
    # possessive bound to the previous thing) reuses the previous route. A
    # command with its OWN numbers/data («نمودار ۱ و ۵») names its subject
    # and routes normally.
    if forced_route is None:
        from universal_mind.conversation_memory import context_params_for, refers_to_last

        if refers_to_last(command):
            # TWO anaphora shapes:
            #  «همان را دوباره بکن» — the command's own words carry NO
            #    capability → reuse the prior run wholesale (route + result).
            #  «نمودارش را بکش» — the command names its OWN capability (chart);
            #    it falls through to the normal pipeline (which charts from
            #    the prior subject surfaced below at the return point).
            from universal_mind.persian_router import route as _route

            own = set(_route(command).capabilities)
            ctx = context_params_for(command)
            if ctx is not None and not own:
                ctx_caps = ctx["route"]
                return {
                    "ok": True, "command": command, "route": ctx_caps,
                    "matched_words": ["ضمیر"], "unknown": [],
                    "extracted_params": {},
                    "result": {"context": {"from_command": ctx["command"],
                                           "reused_route": ctx_caps,
                                           "prior_result": ctx["result"]}},
                    "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
                    "agent_report": (
                        f"همان مورد قبلی را دوباره اجرا کردم: «{ctx['command']}» "
                        f"({', '.join(ctx_caps)})."
                    ),
                    "_registry": registry or ToolRegistry(),
                }
            if ctx is not None and own:
                # The command charts/crafts its own subject — remember WHICH
                # prior run it is derived from (surface at the return below).
                _ANAPHORA_SUBJECT["command"] = ctx["command"]

    # OPERATOR PREFERENCES — «همیشه نمودار میله‌ای دوست دارم» is stored,
    # acknowledged, and shapes every FUTURE chart. The system gets personal.
    if forced_route is None:
        from universal_mind import operator_preferences as prefs

        if prefs.remember_from_command(command):
            return {
                "ok": True, "command": command, "route": ["preference"],
                "matched_words": ["همیشه"], "unknown": [],
                "extracted_params": {},
                "result": {"preference": {"stored": True}},
                "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
                "agent_report": "یاد گرفتم! از این به بعد پیشفرضت را اعمال میکنم.",
                "_registry": registry or ToolRegistry(),
            }

    # «وضعیت» — the agent's status board: every goal, its state and verdict.
    if forced_route is None and (command.strip().startswith("وضعیت") or command.strip() in ("چی شد؟", "چه خبر")):
        from universal_mind.agent_loop import _ensure_goals_table

        db = _status_store()
        _ensure_goals_table(db)
        q = db.query(
            "SELECT goal, next_step, state, outcomes FROM goals "
            "WHERE state != 'archived' ORDER BY id DESC LIMIT 10"
        )
        rows = q["rows"] if q.get("ok") else []
        state_fa = {"done": "✅ تمام", "stopped": "⏸ متوقف", "active": "▶ فعال"}
        if not rows:
            report = "هنوز هدفی ثبت نشده. با «هدف: ...» شروع کن."
        else:
            import json as _json

            fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
            lines = []
            for g in rows:
                try:
                    outcomes = _json.loads(g.get("outcomes") or "[]")
                    last_exc = outcomes[-1]["excellence"] if outcomes else None
                    verdict = (
                        str(round(float(last_exc), 2)).translate(fa)
                        if last_exc is not None else "—"
                    )
                except (ValueError, KeyError, TypeError):
                    verdict = "—"
                goal_fa = str(g["goal"]).translate(fa)  # the operator's digits,
                # rendered Persian (the STORED text stays verbatim — the
                # RENDERING is ours)
                lines.append(
                    f"{state_fa.get(g['state'], g['state'])} {goal_fa} "
                    f"(گام بعدی: {str(g['next_step']).translate(fa)}"
                    f"{'، آخرین داوری: ' + verdict if verdict != '—' else ''})"
                )
            report = "\n".join(lines)
        return {
            "ok": True, "command": command, "route": ["goal"],
            "matched_words": ["وضعیت"], "unknown": [],
            "extracted_params": {},
            "result": {"goal": {"finished": True, "steps": 0, "report": report}},
            "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
            "agent_report": report,
            "_registry": registry or ToolRegistry(),
        }

    # «ادامه بده» — the shortest possible resume: every STOPPED goal is
    # resumed from its exact failing step. The human phrasing of recovery.
    if forced_route is None and command.strip().startswith("ادامه"):
        from universal_mind.agent_loop import _ensure_goals_table

        db = _status_store()
        _ensure_goals_table(db)
        q = db.query("SELECT id FROM goals WHERE state = 'stopped' ORDER BY id")
        stopped = [int(r["id"]) for r in q["rows"]] if q.get("ok") else []
        # POISONED goals are refused with the warning — a blind re-run of a
        # 3x-failed step is a retry loop, not recovery.
        try:
            from universal_mind.agent_loop import _poisoned_goals

            poisoned = set(_poisoned_goals())
        except Exception:  # noqa: BLE001
            poisoned = set()
        safe = [gid for gid in stopped if gid not in poisoned]
        if poisoned and not safe:
            fa_p = str(len(poisoned)).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            return {
                "ok": True, "command": command, "route": ["goal"],
                "matched_words": ["ادامه"], "unknown": [],
                "extracted_params": {},
                "result": {"goal": {"finished": True, "steps": 0,
                                    "report": f"⚠️ {fa_p} هدف زهرآلود است (گامی ۳+ بار شکست خورده) — گام را اصلاح کن یا هدف را آرشیو کن"}},
                "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
                "agent_report": f"⚠️ {fa_p} هدف زهرآلود است (گامی ۳+ بار شکست خورده) — گام را اصلاح کن یا هدف را آرشیو کن",
                "_registry": registry or ToolRegistry(),
            }
        stopped = safe
        if not stopped:
            return {
                "ok": True, "command": command, "route": ["goal"],
                "matched_words": ["ادامه"], "unknown": [],
                "extracted_params": {}, "result": {"goal": {"finished": True, "steps": 0,
                                                            "report": "هدفی متوقف نشده که ادامه بدهم."}},
                "errors": {}, "durations_ms": {}, "flows": [], "judgment": {},
                "agent_report": "هدفی متوقف نشده که ادامه بدهم.",
                "_registry": registry or ToolRegistry(),
            }
        from universal_mind.agent_loop import goal_run_report, run_goal

        reports = [goal_run_report(run_goal(gid)) for gid in stopped[:3]]
        joined = "\n\n".join(reports)
        all_finished = "ناتمام" not in joined
        return {
            "ok": all_finished, "command": command, "route": ["goal"],
            "matched_words": ["ادامه"], "unknown": [],
            "extracted_params": {},
            "result": {"goal": {"finished": all_finished, "steps": len(stopped), "report": joined}},
            "errors": {} if all_finished else {"goal": "بیش از سه هدف متوقف است — بقیه را با یک «ادامه بده»ی دیگر بگیر"},
            "durations_ms": {}, "flows": [], "judgment": {},
            "agent_report": joined,
            "_registry": registry or ToolRegistry(),
        }

    if forced_route is None and "هدف" in command and ":" in command:
        from universal_mind.goal_parser import parse_goal

        parsed = parse_goal(command)
        # NESTED-GOAL GUARD: a step that is itself «هدف: ...» would re-enter
        # the agent layer recursively (goal-in-goal-in-goal...). The guard
        # flattens it ONCE — the inner goal's steps join the outer goal's
        # steps — and the recursion ends. (Caught live: the error text was
        # literally 'the goal of the goal of the goal' one level per retry.)
        if parsed is not None:
            flat: list[str] = []
            for step in parsed.steps:
                if "هدف" in step and ":" in step:
                    inner = parse_goal(step)
                    if inner is not None:
                        flat.extend(inner.steps)
                        continue
                flat.append(step)
            if flat and flat != list(parsed.steps):
                from dataclasses import replace as _dc_replace

                parsed = _dc_replace(parsed, steps=tuple(flat))
        if parsed is not None:
            from universal_mind.agent_loop import goal_run_report, run_goal, start_goal

            started = start_goal(parsed.text, parsed.steps, getattr(parsed, "guarded", None))
            result = run_goal(started["goal_id"])
            report = goal_run_report(result)
            return {
                "ok": result.finished,
                "command": command,
                "route": ["goal"],
                "matched_words": ["هدف"],
                "unknown": [],
                "extracted_params": {},
                "result": {"goal": {"finished": result.finished,
                                    "steps": len(result.steps),
                                    "report": report}},
                "errors": {} if result.finished else {"goal": result.reasoning},
                "durations_ms": {},
                "flows": [],
                "judgment": {},
                "agent_report": report,
                "_registry": registry or ToolRegistry(),
            }

        # (the ordinary command path)
    """
    Returns a JSON-ready payload: the route (capabilities, matched words) plus
    the real per-capability results from orchestrate. A command that matches
    nothing returns ok=False with the honest reason — never a fabricated chain.

    ``forced_route`` overrides the vocabulary-derived route (used by contested
    execution to run a specific candidate chain through the SAME real engine —
    the contest must compare like with like, not two different engines).
    """
    from universal_mind.orchestration import orchestrate
    from universal_mind.persian_params import extract_params
    from universal_mind.real_tool_registry import (
        real_connector_factory,
    )
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
    )
    from universal_mind.tool_registry import (
        ToolRegistry as _Registry,
    )

    # R39: THE EMPTY BAND — «» (nothing typed) is not an error to fail on
    # silently; the operator gets a warm, honest hand-off instead of a hole.
    if forced_route is None and not command.strip():
        return {
            "ok": False,
            "command": command,
            "route": [],
            "error": "فرمانی نوشته نشده — چی بگم، چی بسازم؟",
            "unknown": [],
            "agent_report": "چیزی ننوشتی. یک فرمان کامل بنویس — مثلا: «نمودار ۱ و ۵ را بکش» یا «میانگین ۵ و ۷ را حساب کن».",
            "_registry": registry or ToolRegistry(),
        }

    # R44-1: with the explain marker stripped, the ROUTE (and every
    # extraction below) reads the WORK command — «... — توضیح بده» routes
    # «...», never the marker itself.
    route_result = route(_work_command if _explain else command)
    if not route_result.ok and forced_route is None and not _explain:
        # R39: THE UNKNOWN BAND — failure with a SUGGESTION. The router never
        # leaves the operator alone with a bare "nothing recognized": it offers
        # the nearest known words (edit distance), so a typo is one step from
        # recovery instead of a dead end.
        from universal_mind.spelling_recovery import suggest_for

        suggestion = suggest_for(command)
        return {
            "ok": False,
            "command": command,
            "error": "هیچ قابلیتی شناخته نشد",
            "unknown": list(route_result.unknown),
            "suggestions": suggestion,
            "agent_report": (
                "این فرمان را نشناختم. شاید منظورت یکی از اینها بود: "
                + "، ".join(f"«{s}»" for s in suggestion[:3]) + "؟"
                if suggestion else "این فرمان را نشناختم."
            ),
        }

    # A forced route (contested execution) runs its OWN candidate chain; the
    # vocabulary route is still computed so matched_words stays honest.
    caps = list(forced_route) if forced_route else list(route_result.capabilities)
    reg = registry if registry is not None else _Registry()
    for cap in caps:
        reg.register(
            ToolEntry(
                name=f"fa-{cap}",
                capability=cap,
                connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                absorbable=True,
            )
        )

    # Real parameters extracted FROM the command itself: «میانگین ۲ و ۴» must
    # compute [2, 4], not a default series. A capability receives only the params
    # its contract accepts (the dispatch constrains what it is given).
    _source_command = _work_command if _explain else command
    extracted = params or {cap: extract_params(_source_command, cap) for cap in caps}

    # The dependency planner: reorder by REAL needs (a consumer after its
    # producer, even when said backwards) and choose the operation that uses
    # what the chain produces. Explicit sentence params always win.
    from universal_mind.dependency_planner import plan_chain, plan_params as _plan_params

    plan = plan_chain(caps, extracted)
    caps = [step.capability for step in plan.steps]  # the dependency-respecting order
    planned_params = _plan_params(plan)

    # R44-1/R44-2 — THE PLAN, EXPLAINED: «توضیح بده» / dry-run builds the
    # full Persian program (steps + reasons + learned lessons + preferences)
    # and STOPS — zero side effects, zero files, zero history rows. The
    # operator sees WHY before the platform DOES.
    if explain_only:
        return _explain_payload(_source_command, route_result, plan, extracted, params is not None)
    capability_params = {
        cap: {**planned_params.get(cap, {}), **extracted.get(cap, {})}
        for cap in caps
    }
    # R44-7 — THE PARAMETER A/B: a genuinely ambiguous chart kind («نمودارش کن»,
    # no named kind) runs as a REAL contest — the two best-fitting variants on
    # the same series, ARETĒ judges both, the winner ships with the ruling
    # announced. A NAMED kind (میلهای/دایرهای/خطی) or a stored preference never
    # contests — the operator's word wins, no theater.
    if "chart" in caps and forced_route is None and not _explain:
        from universal_mind.ab_contest import kind_ambiguity, run_ab

        if kind_ambiguity(command, capability_params.get("chart")):
            try:
                from universal_mind.chart_suite import ChartSuiteConnector
                from universal_mind.tool_registry import (
                    ConnectionMechanism,
                    ToolConnectionSpec,
                    ToolEntry,
                )

                def _run_variant(vparams: dict[str, Any]) -> dict[str, Any]:
                    conn = ChartSuiteConnector()
                    spec = ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused")
                    out = conn.connect(spec, vparams)
                    return {"ok": out.ok, "result": {"chart": out.output}, "errors": {} if out.ok else {"chart": out.error}}

                ab = run_ab(command, capability_params["chart"], _run_variant)
                if ab.get("ok"):
                    # the winner's chart result replaces the chart step's params —
                    # the orchestration below runs pdf on the WON artifact.
                    capability_params["chart"] = {"operation": ab["ab_contest"]["winner"], "_ab_shipped": ab["result"]["chart"]}
                    capability_params["_ab_note"] = {"_note": ab["ab_contest"]["reasoning"]}
            except Exception:  # noqa: BLE001 — the contest is a lens, never a blocker
                pass
    # R37-L4: remembered operator preferences shape the params — the
    # command's own words already won above; a preference fills only
    # what the sentence did NOT say.
    try:
        from universal_mind import operator_preferences as _prefs

        capability_params = _prefs.apply_to(capability_params)
    except Exception:  # noqa: BLE001 — preferences are a courtesy, never a blocker
        pass

    # A chain of 2+ capabilities flows by default: one program's real output
    # becomes the next program's input (chart → pdf embeds the real chart).
    syn = orchestrate(
        reg,
        caps,
        connector_factory=real_connector_factory,
        capability_params=capability_params,
        flow=len(caps) > 1,
        command=command,
    )
    # ---- The quality gate: judgment must change behavior, not just grade it.
    # When ARETĒ grades the planned run weak (below the bar), the platform
    # self-repairs: it runs the honest rival order and ships the best REAL
    # verdict. Every attempt stays in the ledger; nothing is fabricated.
    # (A forced_route call IS a gate candidate — the gate runs one level only.)
    if forced_route is None:
        from universal_mind.quality_gate import run_with_quality_gate
        from universal_mind.success_predictor import predict_success

        # THE PRE-RUN VERDICT: the chain's earned expectation sets the bar —
        # a chain that has failed before is judged stricter, not blindly.
        prediction = predict_success(tuple(caps))
        dynamic_bar = prediction.recommended_bar

        def _run_candidate(candidate: tuple[str, ...]) -> dict[str, Any]:
            return route_and_run(command, registry=None, params=None, forced_route=list(candidate))

        gate = run_with_quality_gate(command, tuple(caps), _run_candidate, bar=dynamic_bar)
        if gate.repaired:
            # The shipped attempt replaces the weak one; the operator sees the truth.
            # Surface the anaphora subject too — this is still the OUTER call.
            _subj = _ANAPHORA_SUBJECT.get("command")
            shipped = {**gate.shipped.payload, "gate_reasoning": gate.reasoning, "attempts": len(gate.attempts)}
            if _subj:
                shipped.setdefault("result", {})["anaphora_of"] = _subj
                _ANAPHORA_SUBJECT.clear()
            return shipped
    # The payload the ARETĒ judge reads (the same shape route_and_run returns).
    run_payload_preview = {
        "ok": syn.ok,
        "command": command,
        "route": caps,
        "result": syn.output["synthesized_from"] if isinstance(syn.output, dict) else {},
        "errors": {s.capability: s.error for s in syn.sub_outputs if not s.ok},
        "durations_ms": {s.capability: round(s.duration_ms, 3) for s in syn.sub_outputs},
    }
    # R44-7: the A/B ruling rides the payload — the Persian report announces it.
    _ab_note = (capability_params.get("_ab_note") or {}).get("_note")
    if _ab_note:
        run_payload_preview["ab_ruling"] = _ab_note

    # THE SESSION counts every real run (one sitting, one core, every face).
    try:
        from universal_mind.session_core import SessionCore

        session = SessionCore.current()
        session.add("runs")
        if syn.ok:
            session.add("ok_runs")
        session.add("flows", len(syn.output.get("flows", [])) if isinstance(syn.output, dict) else 0)
    except Exception:  # noqa: BLE001 — counting is a lens, never a blocker
        pass

    # Virtue-judge THIS run with ARETĒ (the same arbitrator that judges
    # specialist disputes now judges the platform's own real work).
    judgment: dict[str, Any] = {}
    try:
        from universal_mind.arete.run_judgment import judge_run

        judgment = judge_run(run_payload_preview)
    except Exception as exc:  # noqa: BLE001 — judgment is a lens, never a blocker
        import sys

        print(f"[arete] داوری اجرا ناموفق بود: {exc}", file=sys.stderr)

    # Record the real run to the persistent history (the advisor learns from it).
    # An honest ENVIRONMENT refusal (e.g. Persian speech with no fa voice) is
    # 'blocked_env', not a failure — the predictor must not learn pessimism
    # from the environment's missing pieces.
    try:
        from universal_mind.run_history import RunHistory

        outcome_class = ""
        if not syn.ok:
            # R43: read the errors where they really live — sub_outputs'
            # error fields (syn.output carries no "errors" key, so the old
            # read was ALWAYS empty and every refusal landed as a failure).
            err_text = " ".join(
                str(s.error) for s in syn.sub_outputs if not s.ok and s.error
            )
            if "صدای فارسی" in err_text:
                outcome_class = "blocked_env"
            # A missing-parameter refusal («کدام سایت؟ آدرس را بده») is the
            # operator being asked, NOT the chain failing — the predictor must
            # not learn pessimism from a question (176 rows of it were recorded
            # as failures from «جستجو کن» alone).
            elif any(
                marker in err_text
                for marker in ("کدام ", "را بده", "بده —", "؟", "نام فایل", "مسیر")
            ):
                outcome_class = "needs_param"
        flows = syn.output.get("flows") if isinstance(syn.output, dict) else None
        RunHistory().record(command, caps, syn.ok,
                            excellence=judgment.get("excellence"),
                            outcome_class=outcome_class,
                            flows=list(flows) if flows else None)
        # R38-L3: the conversation's last context — what the NEXT anaphoric
        # command («نمودارش را بکش») will refer to. Only successful runs.
        if syn.ok:
            try:
                from universal_mind.conversation_memory import save_context

                save_context(command, caps, syn.output.get("synthesized_from") or {})
            except Exception:  # noqa: BLE001 — the memory is a courtesy
                pass
    except Exception as exc:  # noqa: BLE001 — a failed history write never breaks the run
        import sys

        print(f"[history] ثبت اجرا ناموفق بود: {exc}", file=sys.stderr)

    # Teach the planner: fold each capability's REAL verdict into the lessons
    # table (successes only), so the needs table earns its entries over time.
    try:
        from universal_mind.planner_learning import teach

        for sub in syn.sub_outputs:
            if not sub.ok:
                continue
            operation = (capability_params.get(sub.capability) or {}).get("operation")
            teach(sub.capability, str(operation) if operation else "",
                  float(judgment.get("excellence") or 0.0), True)
    except Exception as exc:  # noqa: BLE001 — teaching is a bonus, never fatal
        import sys

        print(f"[planner-learning] آموزش ناموفق بود: {exc}", file=sys.stderr)
    try:
        from universal_mind.session_core import SessionCore

        SessionCore.current().add("judged")
    except Exception:  # noqa: BLE001
        pass
    payload = {
        "ok": syn.ok,
        "command": command,
        "route": caps,
        "matched_words": list(route_result.matched_words),
        "unknown": list(route_result.unknown),
        "extracted_params": capability_params,
        "result": syn.output["synthesized_from"],
        "flows": syn.output.get("flows", []) if isinstance(syn.output, dict) else [],
        "judgment": judgment,
        "errors": {s.capability: s.error for s in syn.sub_outputs if not s.ok},
        "durations_ms": {s.capability: round(s.duration_ms, 3) for s in syn.sub_outputs},
        "_registry": reg,  # kept internal: the caller may reuse the registry
    }
    # R44-7: the A/B ruling rides the SHIPPED payload too — the judge read the
    # preview; the operator's report reads THIS.
    if _ab_note:
        payload["ab_ruling"] = _ab_note
    anaphora_subject = _ANAPHORA_SUBJECT.get("command")
    if anaphora_subject and forced_route is None:
        payload["result"]["anaphora_of"] = anaphora_subject
        _ANAPHORA_SUBJECT.clear()
    # R38-L1: the fluent report rides IN the payload — CLI, API, the chat tab
    # and the goal loop all read ONE source instead of re-rendering. Only
    # when empty (the reflex/conversational classes fill theirs themselves).
    if not payload.get("agent_report"):
        try:
            from universal_mind.persian_report import persian_report

            payload["agent_report"] = persian_report(payload)
        except Exception:  # noqa: BLE001 — reporting is a courtesy, never a blocker
            pass
    return payload


# R38-L3: which prior run an anaphoric command is derived from. Set by the
# consume branch, surfaced on the return payload. Empty = not anaphoric.
_ANAPHORA_SUBJECT: dict[str, str] = {}


def _explain_payload(
    command: str,
    route_result: PersianRoute,
    plan: Any,
    extracted: dict[str, dict[str, Any]],
    params_given: bool,
) -> dict[str, Any]:
    """The Persian program, EXPLAINED — steps, reasons, evidence — no run.

    R44 items 1+2: the plan the router/planner/lessons/preferences built,
    narrated BEFORE any side effect. Zero files, zero toasts, zero history.
    """
    from universal_mind.persian_report import _fa_num

    steps_fa: list[str] = []
    for i, step in enumerate(plan.steps, 1):
        op = f" با عملیات «{step.operation}»" if step.operation else ""
        steps_fa.append(f"گام {_fa_num(i)}: {step.capability}{op} — {step.reason}")

    notes = list(getattr(plan, "notes", ()) or ())
    if getattr(plan, "reorder_happened", False):
        notes.insert(0, "ترتیب گامها بر اساس نیازِ واقعی اصلاح شد (تولیدکننده قبل از مصرفکننده)")

    sources: list[str] = [f"واژگان: «{'، '.join(route_result.matched_words[:6])}»"]
    if params_given:
        sources.append("پارامترها: صریح از فرمان")
    try:

        _prefs_rows = _status_store().query(
            "SELECT COUNT(*) AS n FROM operator_preferences"
        ).get("rows", [])
        if _prefs_rows and int(_prefs_rows[0]["n"]) > 0:
            sources.append("ترجیحهای یادگرفتهشدهی اپراتور هم اعمال میشوند")
    except Exception:  # noqa: BLE001 — a lens, never a blocker
        pass

    report = "برنامهی اجرا — هنوز اجرا نشده:\n" + "\n".join(
        f"  {s}" for s in steps_fa
    )
    if notes:
        report += "\n" + "\n".join(f"  ⚙ {n}" for n in notes)
    report += "\n  📚 " + "؛ ".join(sources)
    report += '\n  برای اجرا بگو: "اجرا کن"'

    return {
        "ok": True,
        "command": command,
        "route": [s.capability for s in plan.steps],
        "matched_words": list(route_result.matched_words),
        "unknown": list(route_result.unknown),
        "extracted_params": extracted,
        "result": {"planned": True, "executed": False},
        "errors": {},
        "durations_ms": {},
        "flows": [],
        "judgment": {},
        "planned": True,
        "executed": False,
        "plan_report": report,
        "agent_report": report,
    }


def _status_store() -> Any:
    """The persistent goals store, tolerant of a mocked DatabaseSuite class.

    Old-style test isolation replaces the module's DatabaseSuite name with a
    plain lambda; that lambda has no shared_persistent. Fall back to the
    constructor (the lambda accepts persistent=True) — both isolation
    styles keep working.
    """
    from universal_mind.database_suite import DatabaseSuite

    shared = getattr(DatabaseSuite, "shared_persistent", None)
    if shared is not None:
        return DatabaseSuite.shared_persistent()
    return DatabaseSuite(persistent=True)


__all__ = ["PersianRoute", "route", "route_and_run"]