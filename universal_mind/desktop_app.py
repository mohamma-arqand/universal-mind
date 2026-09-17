"""Universal Mind — native Windows desktop application (tkinter).

The operator's face of the super-platform: a real windowed application instead of
a command line. The left pane lists every integrated capability (data, database,
image, chart, pdf, media, archive, compute, notify, clipboard); the middle pane
edits the JSON params; the right pane shows the real result. The same unified
engine (orchestrate + real_tool_registry) runs behind it, so the window is not a
mockup — every button triggers genuine work by the integrated programs.

Run:  python desktop_app.py        (from the repo root, or inside the package dir)
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from universal_mind.orchestration import orchestrate
from universal_mind.real_tool_registry import _REAL_CONNECTORS
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)

_CAPABILITY_DESCRIPTIONS: dict[str, str] = {
    "data": "آمار و تحلیل عددی (numpy): میانگین، انحراف، حل معادله، همبستگی",
    "database": "دیتابیس SQL واقعی (SQLite): جدول، درج، کوئری",
    "image": "پردازش تصویر (Pillow): تبدیل، تغییر اندازه، برش، فیلترها",
    "chart": "نمودار (matplotlib): خطی، میله، دایره، هیستوگرام",
    "pdf": "ساخت PDF (reportlab): سند، جدول، تصویر جاسازیشده",
    "media": "رسانه (ffmpeg): تولید فریم، بازرسی، تبدیل",
    "archive": "فشردهسازی واقعی (gzip)",
    "compute": "اجرای JavaScript واقعی (node)",
    "notify": "نوتیفیکیشن ویندوز (بالون سیستمی)",
    "clipboard": "خواندن/نوشتن کلیپبورد ویندوز",
}

# Preset chains: multi-capability sequences that run with one click. Each step's
# real output feeds the synthesis; the weaver folds all outputs into one artifact.
_PRESET_CHAINS: dict[str, list[str]] = {
    "media → chart → pdf (گزارش تصویری)": ["media", "chart", "pdf"],
    "data → chart → pdf (گزارش داده)": ["data", "chart", "pdf"],
    "media → archive (پشتیبان تصویر)": ["media", "archive"],
    "data → database (ذخیره تحلیل)": ["data", "database"],
    "compute → clipboard (نتیجه در کلیپبورد)": ["compute", "clipboard"],
    "media → notify (اطلاع رسانی پس از کار)": ["media", "notify"],
    "vision → pdf (گزارش بینایی)": ["vision", "pdf"],
    "ai → chart (نمودار یادگیری)": ["ai", "chart"],
    "vision → ai → pdf (تحلیل هوشمند تصویر)": ["vision", "ai", "pdf"],
}

_DEFAULT_PARAMS: dict[str, str] = {
    "data": '{"operation": "stats", "data": [2, 4, 4, 4, 5, 5, 7, 9]}',
    "database": '{"operation": "query"}',
    "image": '{"operation": "info"}',
    "chart": '{"operation": "line", "series": {"a": [1, 3, 2, 5], "b": [2, 2, 4, 4]}}',
    "pdf": '{"operation": "document", "title": "گزارش ذهن یکپارچه", "sections": ["بخش اول", "بخش دوم"]}',
    "media": '{"operation": "generate"}',
    "archive": '{"operation": "compress", "content": "Universal Mind"}',
    "compute": '{"operation": "evaluate", "expression": "2 + 2"}',
    "notify": '{"operation": "notify", "title": "Universal Mind", "body": "Task complete"}',
    "clipboard": '{"operation": "read"}',
}


class MindDesktopApp:
    """The native-window face of the super-platform (tkinter, real engine)."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        root.title("Universal Mind — سیستم یکپارچه")
        root.geometry("1180x680")

        self._build_layout()
        self._populate_capabilities()

    # ------------------------------------------------------------------ layout
    def _build_layout(self) -> None:
        header = ttk.Frame(self._root, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="◆ Universal Mind — پلتفرم یکپارچه",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="هر دکمه کارِ واقعی توسط برنامههای یکپارچه انجام میدهد",
            foreground="#666",
        ).pack(side=tk.LEFT, padx=12)

        body = ttk.Frame(self._root, padding=(8, 0, 8, 8))
        body.pack(fill=tk.BOTH, expand=True)

        self._notebook = ttk.Notebook(body)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # --- Tab 1: single capability (the original three-pane form) ---
        single = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(single, text="تک قابلیت")

        left = ttk.LabelFrame(single, text="قابلیتها", padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y)
        self._cap_list = tk.Listbox(left, width=24, height=24, font=("Segoe UI", 10))
        self._cap_list.pack(fill=tk.Y, expand=True)
        self._cap_list.bind("<<ListboxSelect>>", self._on_select)

        middle = ttk.LabelFrame(single, text="پارامترها (JSON)", padding=6)
        middle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self._params_text = scrolledtext.ScrolledText(middle, height=12, font=("Consolas", 10))
        self._params_text.pack(fill=tk.X)
        self._run_btn = ttk.Button(middle, text="▶ اجرا (کار واقعی)", command=self._run)
        self._run_btn.pack(pady=6, anchor=tk.W)

        ttk.Label(middle, text="نتیجه:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self._result_text = scrolledtext.ScrolledText(middle, height=18, font=("Consolas", 9))
        self._result_text.pack(fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(single, text="وضعیت موتور", padding=6)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        self._status_text = scrolledtext.ScrolledText(right, width=34, height=24, font=("Segoe UI", 9))
        self._status_text.pack(fill=tk.Y, expand=True)
        self._write_status()

        # --- Tab: analytics (تحلیل تاریخچه) ---
        analytics_tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(analytics_tab, text="تحلیل")
        ttk.Button(
            analytics_tab, text="📊 داشبورد را در مرورگر باز کن",
            command=self._open_dashboard,
        ).pack(anchor=tk.W, pady=(0, 6))
        self._analytics_text = scrolledtext.ScrolledText(
            analytics_tab, font=("Segoe UI", 12), wrap=tk.WORD
        )
        self._analytics_text.pack(fill=tk.BOTH, expand=True)
        self._refresh_analytics()

        # --- Tab: schedules (زمانبندیها — the proactive tasks) ---
        sched_tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(sched_tab, text="زمانبندیها")
        sched_top = ttk.LabelFrame(sched_tab, text="زمانبندی جدید", padding=6)
        sched_top.pack(fill=tk.X)
        self._sched_entry = ttk.Entry(sched_top, font=("Segoe UI", 11))
        self._sched_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self._sched_entry.insert(tk.END, "هر روز ساعت ۸ گزارش کامل بده")
        ttk.Button(sched_top, text="＋ ثبت", command=self._register_schedule).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            sched_tab, text="▶ اجرای سررسیدها", command=self._run_schedules,
        ).pack(anchor=tk.W, pady=6)
        ttk.Button(
            sched_tab, text="📁 پوشهها را اسکن کن (فایلهای جدید)", command=self._scan_watchers,
        ).pack(anchor=tk.W, pady=(0, 6))
        self._sched_text = scrolledtext.ScrolledText(
            sched_tab, font=("Segoe UI", 12), wrap=tk.WORD
        )
        self._sched_text.pack(fill=tk.BOTH, expand=True)
        self._refresh_schedules()

        # --- Tab: goals (اهداف — the agent layer) ---
        goals_tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(goals_tab, text="اهداف")
        goals_top = ttk.LabelFrame(goals_tab, text="هدف جدید", padding=6)
        goals_top.pack(fill=tk.X)
        self._goal_entry = ttk.Entry(goals_top, font=("Segoe UI", 11))
        self._goal_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self._goal_entry.insert(tk.END, "هدف: میانگین ۱۰ و ۲۰ را حساب کن و نمودارش کن و گزارش کامل بساز")
        ttk.Button(goals_top, text="🎯 ثبت و اجرا", command=self._run_new_goal).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            goals_tab, text="▶ ادامهی همهی هدفهای متوقفشده", command=self._resume_goals,
        ).pack(anchor=tk.W, pady=6)
        self._goals_text = scrolledtext.ScrolledText(
            goals_tab, font=("Segoe UI", 12), wrap=tk.WORD
        )
        self._goals_text.pack(fill=tk.BOTH, expand=True)
        self._refresh_goals()

        # --- Tab 2: Persian command (فارسی بگو، سیستم اجرا کند) ---
        fa_tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(fa_tab, text="فرمان فارسی")

        fa_top = ttk.LabelFrame(fa_tab, text="فرمان فارسی", padding=6)
        fa_top.pack(fill=tk.X)
        self._fa_entry = ttk.Entry(fa_top, font=("Segoe UI", 11))
        self._fa_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self._fa_entry.insert(tk.END, "محاسبه کن، نمودار بکش و ذخیره کن")
        self._fa_run_btn = ttk.Button(fa_top, text="▶ اجرا", command=self._run_persian)
        self._fa_run_btn.pack(side=tk.LEFT, padx=6)

        # The advisor's live suggestion — learned from the operator's own history.
        advice = ttk.LabelFrame(fa_tab, text="پیشنهاد (از تجربهی اجراهای قبلی)", padding=6)
        advice.pack(fill=tk.X, pady=(4, 0))
        self._fa_advice_label = ttk.Label(
            advice, text="در حال نوشتن فرمان، پیشنهاد همینجا ظاهر میشود…",
            foreground="#667", font=("Segoe UI", 10),
        )
        self._fa_advice_label.pack(anchor=tk.W)
        self._fa_entry.bind("<KeyRelease>", self._on_fa_typing)

        fa_body = ttk.Frame(fa_tab, padding=(0, 6))
        fa_body.pack(fill=tk.BOTH, expand=True)
        fa_left = ttk.LabelFrame(fa_body, text="مسیر و کلمات", padding=6)
        fa_left.pack(side=tk.LEFT, fill=tk.Y)
        self._fa_route_text = scrolledtext.ScrolledText(fa_left, width=38, height=20, font=("Segoe UI", 9))
        self._fa_route_text.pack(fill=tk.Y, expand=True)
        fa_result = ttk.LabelFrame(fa_body, text="نتیجه (کار واقعی)", padding=6)
        fa_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self._fa_result_text = scrolledtext.ScrolledText(fa_result, height=8, font=("Consolas", 9))
        self._fa_result_text.pack(fill=tk.X)
        fa_report = ttk.LabelFrame(fa_result, text="گزارش فارسی", padding=6)
        fa_report.pack(fill=tk.BOTH, expand=True)
        self._fa_report_text = scrolledtext.ScrolledText(
            fa_report, font=("Segoe UI", 11), wrap=tk.WORD
        )
        self._fa_report_text.pack(fill=tk.BOTH, expand=True)
        fa_preview = ttk.LabelFrame(fa_body, text="پیشنمایش", padding=6)
        fa_preview.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self._fa_preview_label = ttk.Label(
            fa_preview, text="تصویر تولیدشده اینجا نمایش داده میشود",
            anchor=tk.CENTER, foreground="#666",
        )
        self._fa_preview_label.pack(fill=tk.BOTH, expand=True)
        self._fa_preview_photo: Any = None  # hold alive for Tk

        # --- Tab 3: chain (multi-capability, one click) ---
        chain_tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(chain_tab, text="زنجیره")

        chain_left = ttk.LabelFrame(chain_tab, text="زنجیرههای آماده", padding=6)
        chain_left.pack(side=tk.LEFT, fill=tk.Y)
        self._chain_list = tk.Listbox(chain_left, width=40, height=24, font=("Segoe UI", 10))
        self._chain_list.pack(fill=tk.Y, expand=True)
        self._refresh_chain_list()
        if self._chain_list.size():
            self._chain_list.selection_set(0)

        # Chain builder: the operator's own sequences, saved to the persistent db.
        builder = ttk.LabelFrame(chain_tab, text="سازنده زنجیره (قابلیتها را به ترتیب انتخاب کن)", padding=6)
        builder.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        self._builder_list = tk.Listbox(builder, width=20, height=5, font=("Segoe UI", 9))
        self._builder_list.pack(side=tk.LEFT, fill=tk.Y)
        self._builder_picked: list[str] = []
        builder_controls = ttk.Frame(builder)
        builder_controls.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        row1 = ttk.Frame(builder_controls)
        row1.pack(fill=tk.X)
        self._builder_choice = ttk.Combobox(row1, values=sorted(_CAPABILITY_DESCRIPTIONS), width=14, state="readonly")
        self._builder_choice.pack(side=tk.LEFT)
        ttk.Button(row1, text="+ افزودن", command=self._builder_add).pack(side=tk.LEFT, padx=3)
        ttk.Button(row1, text="− حذف آخرین", command=self._builder_remove_last).pack(side=tk.LEFT, padx=3)
        ttk.Button(row1, text="پاک کردن", command=self._builder_clear).pack(side=tk.LEFT, padx=3)
        row2 = ttk.Frame(builder_controls)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="نام:").pack(side=tk.LEFT)
        self._builder_name = ttk.Entry(row2, width=28)
        self._builder_name.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="💾 ذخیره زنجیره", command=self._builder_save).pack(side=tk.LEFT, padx=3)
        self._builder_status = ttk.Label(builder_controls, text="", foreground="#2a7")
        self._builder_status.pack(anchor=tk.W)

        chain_right = ttk.LabelFrame(chain_tab, text="نتیجهی زنجیره", padding=6)
        chain_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self._chain_run_btn = ttk.Button(
            chain_right, text="▶ اجرای زنجیره (کار واقعی)", command=self._run_chain
        )
        self._chain_run_btn.pack(anchor=tk.W, pady=4)
        self._chain_result = scrolledtext.ScrolledText(chain_right, height=10, font=("Consolas", 9))
        self._chain_result.pack(fill=tk.X)

        # Graphic preview: the real produced image (chart/media) shown in-window.
        preview_frame = ttk.LabelFrame(chain_tab, text="پیشنمایش (تصویر/نمودار تولیدشده)", padding=6)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self._preview_label = ttk.Label(
            preview_frame, text="پس از اجرای زنجیره، تصویرِ تولیدشده اینجا نمایش داده میشود",
            anchor=tk.CENTER, foreground="#666",
        )
        self._preview_label.pack(fill=tk.BOTH, expand=True)
        self._preview_photo: Any = None  # hold a reference so Tk doesn't GC it
        self._preview_path: str | None = None  # the currently shown artifact
        ttk.Button(
            preview_frame, text="📂 باز کردن پوشه در Explorer", command=self._open_preview_folder
        ).pack(anchor=tk.W, pady=(4, 0))

    def _refresh_schedules(self) -> None:
        """Render the operator's real schedule table (persisted, with status)."""
        from datetime import datetime as _dt

        from universal_mind.scheduler import _next_due, list_schedules

        self._sched_text.delete("1.0", tk.END)
        schedules = list_schedules()
        if not schedules:
            self._sched_text.insert(tk.END, "هنوز زمانبندیای ثبت نشده است.\n")
            return
        now = _dt.now()
        for s in schedules:
            nxt = _next_due(s, now)
            when = nxt.strftime("%H:%M %Y-%m-%d") if nxt else "غیرفعال"
            state = "فعال" if s.active else "غیرفعال"
            self._sched_text.insert(
                tk.END,
                f"• [{state}] {s.command}\n  سررسید بعدی: {when} | آخرین اجرا: {s.last_run[:16] or '—'}\n\n",
            )
        # The folder watchers — the file-event perception channel.
        from universal_mind.scheduler import list_watchers

        watchers = list_watchers()
        if watchers:
            self._sched_text.insert(tk.END, "── پوشههای تحت نظر ───\n")
            for w in watchers:
                state = "فعال" if w["active"] else "غیرفعال"
                self._sched_text.insert(
                    tk.END,
                    f"• [{state}] {w['folder']}\n  فرمان: {w['action']}\n\n",
                )

    def _refresh_goals(self) -> None:
        """Render the operator's real goals with their state and next step."""

        from universal_mind.agent_loop import _ensure_goals_table
        from universal_mind.database_suite import DatabaseSuite

        self._goals_text.delete("1.0", tk.END)
        db = DatabaseSuite(persistent=True)
        _ensure_goals_table(db)
        q = db.query("SELECT id, goal, next_step, state FROM goals ORDER BY id DESC LIMIT 20")
        rows = q["rows"] if q.get("ok") else []
        if not rows:
            self._goals_text.insert(tk.END, "هنوز هدفی ثبت نشده. یک جمله با «هدف:» بنویس.\n")
            return
        state_fa = {"done": "✅ تمام", "stopped": "⏸ متوقف", "active": "▶ فعال"}
        for g in rows:
            self._goals_text.insert(
                tk.END,
                f"• [{state_fa.get(g['state'], str(g['state']))}] {g['goal']}\n"
                f"  گام بعدی: {g['next_step']} | شناسه: {g['id']}\n\n",
            )

    def _run_new_goal(self) -> None:
        """Parse the entry's goal, persist it, run it, and narrate."""
        from universal_mind.agent_loop import goal_run_report, run_goal, start_goal
        from universal_mind.goal_parser import parse_goal

        sentence = self._goal_entry.get().strip()
        parsed = parse_goal(sentence)
        if parsed is None:
            messagebox.showinfo("Universal Mind", "قالب هدف: هدف: گام اول و گام دوم ...")
            return
        started = start_goal(parsed.text, parsed.steps)
        result = run_goal(started["goal_id"])
        self._refresh_goals()
        self._goals_text.insert(tk.END, "\n" + goal_run_report(result) + "\n")

    def _resume_goals(self) -> None:
        """Resume every stopped goal from its exact failing step."""
        from universal_mind.agent_loop import goal_run_report, run_goal
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.agent_loop import _ensure_goals_table

        db = DatabaseSuite(persistent=True)
        _ensure_goals_table(db)
        q = db.query("SELECT id FROM goals WHERE state = 'stopped' ORDER BY id")
        stopped = [int(r["id"]) for r in q["rows"]] if q.get("ok") else []
        if not stopped:
            messagebox.showinfo("Universal Mind", "هدف متوقفشدهای نیست")
            return
        reports = []
        for goal_id in stopped[:3]:
            result = run_goal(goal_id)
            reports.append(goal_run_report(result))
        self._refresh_goals()
        self._goals_text.insert(tk.END, "\n" + "\n\n".join(reports) + "\n")

    def _scan_watchers(self) -> None:
        """Sweep every active folder watcher; report what genuinely fired."""
        from universal_mind.scheduler import scan_watchers

        result = scan_watchers()
        self._refresh_schedules()
        count = result.get("count", 0)
        messagebox.showinfo(
            "Universal Mind",
            f"{count} فایلِ جدید پردازش شد" if count else "فایل جدیدی نبود",
        )

    def _register_schedule(self) -> None:
        """Register the sentence in the entry as a real persisted schedule."""
        from universal_mind.scheduler import register

        sentence = self._sched_entry.get().strip()
        if not sentence:
            messagebox.showinfo("Universal Mind", "یک جملهی زمانبندی بنویس")
            return
        result = register(sentence)
        if result.get("ok"):
            self._refresh_schedules()
        else:
            messagebox.showinfo("Universal Mind", str(result.get("error")))

    def _run_schedules(self) -> None:
        """Fire every due schedule through the real engine."""
        from universal_mind.scheduler import run_due

        result = run_due()
        self._refresh_schedules()
        fired = result.get("count", 0)
        messagebox.showinfo(
            "Universal Mind",
            f"{fired} زمانبندی اجرا شد" if fired else "چیزی سررسید نشده بود",
        )

    def _open_dashboard(self) -> None:
        """Build the REAL dashboard from history and open it in the browser."""
        import subprocess
        import webbrowser

        try:
            from universal_mind.superplatform_dashboard import build_dashboard

            result = build_dashboard()
            if result.get("ok"):
                webbrowser.open(f"file:///{result['path'].replace(chr(92), '/')}")
        except Exception as exc:  # noqa: BLE001 — a view action, never fatal
            messagebox.showinfo("Universal Mind", f"ساخت داشبورد ناموفق بود: {exc}")
            return
        # webbrowser may silently no-op on some setups; explorer is the fallback
        try:
            subprocess.run(["explorer.exe", result["path"]], check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):  # noqa: BLE001 — bonus
            pass

    def _open_preview_folder(self) -> None:
        """Open the produced artifact's folder in Windows Explorer (real)."""
        import subprocess

        path = self._preview_path
        if not path:
            messagebox.showinfo("Universal Mind", "ابتدا یک زنجیره اجرا کن")
            return
        try:
            subprocess.run(["explorer.exe", "/select,", path], check=False, timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showinfo("Universal Mind", f"باز کردن پوشه ناموفق بود: {exc}")

    def _write_status(self) -> None:
        box = self._status_text
        box.configure(state=tk.NORMAL)
        box.delete("1.0", tk.END)
        box.insert(tk.END, "برنامههای یکپارچه:\n\n")
        for cap in sorted(_REAL_CONNECTORS):
            box.insert(tk.END, f"  ✓ {cap}\n")
        box.insert(tk.END, f"\nمجموع: {len(_REAL_CONNECTORS)} قابلیت واقعی\n")
        box.insert(tk.END, "موتور: orchestrate + registry\n")
        box.insert(tk.END, "داوری، حافظه و یادگیری پشت صحنه فعال‌اند")
        box.configure(state=tk.DISABLED)

    def _populate_capabilities(self) -> None:
        for cap in sorted(_CAPABILITY_DESCRIPTIONS):
            if cap in _REAL_CONNECTORS:  # only genuinely wired capabilities
                self._cap_list.insert(tk.END, cap)
        if self._cap_list.size():
            self._cap_list.selection_set(0)
            self._on_select(None)

    # ---------------------------------------------------------------- behavior
    def _selected_capability(self) -> str | None:
        # tkinter's stdlib stubs are untyped (curselection has no annotation).
        selection: tuple[int, ...] = tuple(self._cap_list.curselection())  # type: ignore[no-untyped-call]
        return self._cap_list.get(selection[0]) if selection else None

    def _on_select(self, _event: Any) -> None:
        cap = self._selected_capability()
        if cap is None:
            return
        self._params_text.delete("1.0", tk.END)
        self._params_text.insert(tk.END, _DEFAULT_PARAMS.get(cap, "{}"))

    def _run(self) -> None:
        cap = self._selected_capability()
        if cap is None:
            messagebox.showinfo("Universal Mind", "ابتدا یک قابلیت انتخاب کن")
            return
        raw = self._params_text.get("1.0", tk.END).strip()
        try:
            params = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            messagebox.showerror("JSON نامعتبر", f"پارامترها JSON درست نیست:\n{exc}")
            return

        self._run_btn.configure(state=tk.DISABLED)
        self._show_result("در حال اجرای کارِ واقعی…")
        # Real work off the UI thread, so the window never freezes.
        thread = threading.Thread(target=self._do_work, args=(cap, params), daemon=True)
        thread.start()

    def _do_work(self, cap: str, params: dict[str, Any]) -> None:
        """Run the real engine (orchestrate) and post the result back to the UI."""
        try:
            registry = ToolRegistry()
            registry.register(
                ToolEntry(
                    name=f"app-{cap}",
                    capability=cap,
                    connection=ToolConnectionSpec(
                        mechanism=ConnectionMechanism.SUBPROCESS, command="unused"
                    ),
                    absorbable=True,
                )
            )
            syn = orchestrate(registry, [cap], connector_factory=_factory_for(cap))
            payload = {
                "ok": syn.ok,
                "result": syn.output["synthesized_from"],
                "error": next((s.error for s in syn.sub_outputs if not s.ok), ""),
                "duration_ms": next(
                    (s.duration_ms for s in syn.sub_outputs if s.capability == cap), 0.0
                ),
            }
        except Exception as exc:  # noqa: BLE001 — a crashed engine is a real error
            payload = {"ok": False, "result": None, "error": str(exc)}
        self._root.after(0, self._post_result, payload)

    def _show_result(self, text: str) -> None:
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert(tk.END, text)

    # ------------------------------------------------------------------ chain
    def _selected_chain(self) -> list[str] | None:
        selection: tuple[int, ...] = tuple(self._chain_list.curselection())  # type: ignore[no-untyped-call]
        if not selection:
            return None
        return self._chain_names[selection[0]][1]

    def _run_chain(self) -> None:
        caps = self._selected_chain()
        if not caps:
            messagebox.showinfo("Universal Mind", "ابتدا یک زنجیره انتخاب کن")
            return
        self._chain_run_btn.configure(state=tk.DISABLED)
        self._chain_result.delete("1.0", tk.END)
        self._chain_result.insert(tk.END, f"در حال اجرای زنجیره: {' → '.join(caps)}\n\n")
        thread = threading.Thread(target=self._do_chain_work, args=(caps,), daemon=True)
        thread.start()

    def _do_chain_work(self, caps: list[str]) -> None:
        """Run the real multi-capability synthesis (all real programs at once)."""
        try:
            registry = ToolRegistry()
            for cap in caps:
                registry.register(
                    ToolEntry(
                        name=f"chain-{cap}",
                        capability=cap,
                        connection=ToolConnectionSpec(
                            mechanism=ConnectionMechanism.SUBPROCESS, command="unused"
                        ),
                        absorbable=True,
                    )
                )
            syn = orchestrate(registry, caps, connector_factory=_multi_factory(caps))
            payload = {
                "ok": syn.ok,
                "chain": caps,
                "results": syn.output["synthesized_from"],
                "errors": {s.capability: s.error for s in syn.sub_outputs if not s.ok},
                "durations_ms": {s.capability: s.duration_ms for s in syn.sub_outputs},
            }
        except Exception as exc:  # noqa: BLE001 — a crashed engine is a real error
            payload = {"ok": False, "chain": caps, "error": str(exc)}
        self._root.after(0, self._post_chain_result, payload)

    # ------------------------------------------------------------- builder
    def _refresh_chain_list(self) -> None:
        """List presets + the operator's saved custom chains (real, persistent)."""
        from universal_mind.chains_store import ChainsStore

        self._chain_list.delete(0, tk.END)
        self._chain_names: list[tuple[str, list[str]]] = []
        for name, caps in _PRESET_CHAINS.items():
            self._chain_list.insert(tk.END, name)
            self._chain_names.append((name, caps))
        try:
            for chain in ChainsStore().load():
                label = f"{chain.name} (ذخیرهشده)"
                self._chain_list.insert(tk.END, label)
                self._chain_names.append((label, list(chain.capabilities)))
        except Exception as exc:  # noqa: BLE001 — a missing store never breaks the window
            self._chain_list.insert(tk.END, f"(خطا در خواندن زنجیرهها: {exc})")

    def _builder_add(self) -> None:
        cap = self._builder_choice.get()
        if not cap:
            return
        self._builder_picked.append(cap)
        self._builder_list.insert(tk.END, cap)

    def _builder_remove_last(self) -> None:
        if self._builder_picked:
            self._builder_picked.pop()
            self._builder_list.delete(tk.END)

    def _builder_clear(self) -> None:
        self._builder_picked.clear()
        self._builder_list.delete(0, tk.END)

    def _builder_save(self) -> None:
        from universal_mind.chains_store import ChainsStore

        name = self._builder_name.get().strip()
        if not name:
            messagebox.showinfo("Universal Mind", "یک نام برای زنجیره بنویس")
            return
        if not self._builder_picked:
            messagebox.showinfo("Universal Mind", "ابتدا قابلیت انتخاب کن")
            return
        try:
            ChainsStore().save(name, list(self._builder_picked))
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("ذخیره ناموفق", str(exc))
            return
        self._builder_status.configure(text=f"✓ ذخیره شد: {name}")
        self._builder_clear()
        self._builder_name.delete(0, tk.END)
        self._refresh_chain_list()

    def _post_chain_result(self, payload: dict[str, Any]) -> None:
        self._chain_run_btn.configure(state=tk.NORMAL)
        self._chain_result.delete("1.0", tk.END)
        self._chain_result.insert(tk.END, json.dumps(payload, indent=2, ensure_ascii=False))
        # Show the first real image the chain produced, directly in the window.
        self._show_preview(_first_image_from(payload.get("results", {})))

    def _post_result(self, payload: dict[str, Any]) -> None:
        self._run_btn.configure(state=tk.NORMAL)
        self._show_result(json.dumps(payload, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------- persian
    def _on_fa_typing(self, _event: Any) -> None:
        """Live advice as the operator types — the chain history suggests."""
        command = self._fa_entry.get().strip()
        if len(command) < 6:
            self._fa_advice_label.configure(
                text="در حال نوشتن فرمان، پیشنهاد همینجا ظاهر میشود…", foreground="#667"
            )
            return
        try:
            from universal_mind.persian_report import _CAP_FA
            from universal_mind.run_history import ChainAdvisor

            suggestion = ChainAdvisor().advise(command)
        except Exception:  # noqa: BLE001 — advice is a bonus, never fatal
            suggestion = None
        if suggestion is None:
            self._fa_advice_label.configure(
                text="هنوز تجربهای برای این فرمان نیست — اجرا کن تا یاد بگیرد", foreground="#667"
            )
        else:
            chain_fa = " → ".join(_CAP_FA.get(c, c) for c in suggestion.route)
            quality = (
                f"کیفیت داوری {suggestion.mean_excellence:.0%}"
                if suggestion.mean_excellence > 0.0
                else "بدون داوری هنوز"
            )
            completion = ""
            try:
                from universal_mind.run_history import ChainAdvisor

                hint = ChainAdvisor().completion_hint(command)
                if hint:
                    completion = f"\n{hint}"
            except Exception:  # noqa: BLE001 — a hint is a bonus, never fatal
                pass
            self._fa_advice_label.configure(
                text=(
                    f"💡 پیشنهاد: {chain_fa} "
                    f"({suggestion.succeeded_runs} اجرای موفق، {quality}){completion}"
                ),
                foreground="#2a7",
            )

    def _refresh_analytics(self) -> None:
        """Render the real history statistics (the operator's actual usage)."""
        from universal_mind.history_analytics import analytics_report, analyze_history

        self._analytics_text.delete("1.0", tk.END)
        try:
            self._analytics_text.insert(tk.END, analytics_report(analyze_history()))
        except Exception as exc:  # noqa: BLE001 — analytics is a view, never fatal
            self._analytics_text.insert(tk.END, f"(تحلیل ناموجود: {exc})")

    def _run_persian(self) -> None:
        command = self._fa_entry.get().strip()
        if not command:
            messagebox.showinfo("Universal Mind", "یک فرمان فارسی بنویس")
            return
        self._fa_run_btn.configure(state=tk.DISABLED)
        self._fa_route_text.delete("1.0", tk.END)
        self._fa_route_text.insert(tk.END, "در حال تحلیل فرمان…")
        self._fa_result_text.delete("1.0", tk.END)
        thread = threading.Thread(target=self._do_persian_work, args=(command,), daemon=True)
        thread.start()

    def _do_persian_work(self, command: str) -> None:
        """Route the Persian command and run the real chain (unified engine)."""
        try:
            from universal_mind.persian_router import route_and_run

            payload = route_and_run(command)
            payload.pop("_registry", None)  # internal: never serialize the registry
        except Exception as exc:  # noqa: BLE001 — a crashed engine is a real error
            payload = {"ok": False, "command": command, "error": str(exc)}
        self._root.after(0, self._post_persian, payload)

    def _post_persian(self, payload: dict[str, Any]) -> None:
        self._fa_run_btn.configure(state=tk.NORMAL)
        # Route pane: human-readable Persian summary.
        self._fa_route_text.delete("1.0", tk.END)
        route_caps = payload.get("route", [])
        self._fa_route_text.insert(
            tk.END,
            f"فرمان: {payload.get('command', '')}\n\n"
            f"مسیر اجرا: {' → '.join(route_caps) if route_caps else '—'}\n"
            f"کلمات شناختهشده: {', '.join(payload.get('matched_words', [])) or '—'}\n"
            f"کلمات ناشناخته: {', '.join(payload.get('unknown', [])) or '—'}\n"
            f"وضعیت: {'✓ موفق' if payload.get('ok') else '✗ ناموفق'}",
        )
        self._fa_result_text.delete("1.0", tk.END)
        self._fa_result_text.insert(tk.END, json.dumps(payload, indent=2, ensure_ascii=False))
        # The fluent Persian report — what the operator actually reads.
        from universal_mind.persian_report import persian_report

        self._fa_report_text.delete("1.0", tk.END)
        self._fa_report_text.insert(tk.END, persian_report(payload))
        # The analytics tab reflects the just-recorded run too.
        self._refresh_analytics()
        # Show the produced image in the Persian tab's preview pane too.
        self._show_fa_preview(_first_image_from(payload.get("result", {})))

    def _show_preview(self, image_path: str | None) -> None:
        """Show the chain result image in the chain tab's preview pane."""
        self._show_preview_in(
            self._preview_label, lambda: setattr(self, "_preview_photo", None),
            lambda photo: setattr(self, "_preview_photo", photo), image_path,
            empty_text="این زنجیره تصویری تولید نکرد",
        )

    def _show_fa_preview(self, image_path: str | None) -> None:
        """Show the Persian-command result image in the Persian tab's pane."""
        self._show_preview_in(
            self._fa_preview_label, lambda: setattr(self, "_fa_preview_photo", None),
            lambda photo: setattr(self, "_fa_preview_photo", photo), image_path,
            empty_text="این فرمان تصویری تولید نکرد",
        )

    def _show_preview_in(
        self, label: ttk.Label, clear_photo: Any, set_photo: Any,
        image_path: str | None, *, empty_text: str,
    ) -> None:
        """Display a real produced image inside a label (resized to fit)."""
        from PIL import Image, ImageTk

        if not image_path:
            label.configure(text=empty_text, foreground="#666", image="")
            clear_photo()
            return
        try:
            with Image.open(image_path) as im:
                im.thumbnail((420, 320))
                photo = ImageTk.PhotoImage(im)
        except Exception as exc:  # noqa: BLE001 — a broken preview is not fatal
            label.configure(text=f"(پیشنمایش ناممکن: {exc})", foreground="#a00", image="")
            clear_photo()
            return
        set_photo(photo)  # keep alive: Tk only renders referenced images
        label.configure(image=photo, text="")
        self._preview_path = image_path  # remember what is on screen


def _first_image_from(results: dict[str, Any]) -> str | None:
    """The first real image file among a chain's outputs (chart/media/image/
    vision), or None. Vision's edge/contour images are real PNGs too."""
    for cap in ("chart", "media", "image", "vision"):
        entry = results.get(cap)
        if isinstance(entry, dict) and entry.get("path"):
            path = str(entry["path"])
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                return path
    return None


def _factory_for(cap: str) -> Callable[[ToolEntry], Any]:
    """Return a connector factory that resolves `cap` to its real connector."""
    from universal_mind.real_tool_registry import real_connector_factory

    def factory(tool: ToolEntry) -> Any:
        constructor = _REAL_CONNECTORS.get(cap)
        if constructor is not None:
            return constructor()
        return real_connector_factory(tool)

    return factory


def _multi_factory(caps: list[str]) -> Callable[[ToolEntry], Any]:
    """A connector factory routing EACH requested capability to its real connector
    (so a chain like media→archive drives two different real programs in one run)."""
    from universal_mind.real_tool_registry import real_connector_factory

    def factory(tool: ToolEntry) -> Any:
        constructor = _REAL_CONNECTORS.get(tool.capability)
        if constructor is not None and tool.capability in caps:
            return constructor()
        return real_connector_factory(tool)

    return factory


def main() -> None:
    root = tk.Tk()
    MindDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()