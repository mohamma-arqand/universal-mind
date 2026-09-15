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

        fa_body = ttk.Frame(fa_tab, padding=(0, 6))
        fa_body.pack(fill=tk.BOTH, expand=True)
        fa_left = ttk.LabelFrame(fa_body, text="مسیر و کلمات", padding=6)
        fa_left.pack(side=tk.LEFT, fill=tk.Y)
        self._fa_route_text = scrolledtext.ScrolledText(fa_left, width=38, height=20, font=("Segoe UI", 9))
        self._fa_route_text.pack(fill=tk.Y, expand=True)
        fa_result = ttk.LabelFrame(fa_body, text="نتیجه (کار واقعی)", padding=6)
        fa_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self._fa_result_text = scrolledtext.ScrolledText(fa_result, font=("Consolas", 9))
        self._fa_result_text.pack(fill=tk.BOTH, expand=True)
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
        for name in _PRESET_CHAINS:
            self._chain_list.insert(tk.END, name)
        if self._chain_list.size():
            self._chain_list.selection_set(0)

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
        name = self._chain_list.get(selection[0])
        return _PRESET_CHAINS.get(name)

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