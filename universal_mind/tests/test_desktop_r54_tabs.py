"""R54 — DESKTOP UX WAVES: the two new tabs, live.

یادآورها (the one-shot reminder tab): register via the REAL router,
list the REAL kind='once' rows with Persian next-due. سیستم (the machine
vitals tab): the REAL SystemStatusTool numbers. Both must render without
crashing on a live Tk root — the modal-bomb lesson of R52.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Iterator

import pytest

from universal_mind.desktop_app import MindDesktopApp


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def tk_root() -> Iterator[tk.Tk]:
    """A hidden Tk root (no window shown, but the widget tree is real)."""
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("no display available for tkinter")
    yield root
    root.destroy()


def _app(tk_root: tk.Tk) -> MindDesktopApp:
    return MindDesktopApp(tk_root)


class TestReminderTab:
    def test_register_via_the_real_router(self, tk_root: tk.Tk) -> None:
        from universal_mind.scheduler import delete_schedule, list_schedules

        app = _app(tk_root)
        app._rem_entry.delete(0, tk.END)
        app._rem_entry.insert(0, "یادم بنداز که فردا ساعت ۸ تست دسکتاپ باشم")
        app._register_reminder()
        onces = [s for s in list_schedules()
                 if s.kind == "once" and "تست دسکتاپ" in s.command]
        assert onces, "the reminder did not persist through the real router"
        for s in onces:
            delete_schedule(s.schedule_id)

    def test_list_renders_the_real_rows(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._refresh_reminders()
        rendered = app._rem_text.get("1.0", tk.END)
        assert "یادآور" in rendered  # the empty state or the real list — Persian

    def test_empty_entry_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._rem_entry.delete(0, tk.END)
        app._register_reminder()
        rendered = app._rem_text.get("1.0", tk.END)
        assert "بنویس" in rendered or "یادآوری" in rendered


class TestSystemTab:
    def test_renders_real_vitals(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._refresh_sysstatus()
        rendered = app._sys_text.get("1.0", tk.END)
        # the REAL machine always shows RAM or a disk; an honest note is fine too
        assert any(w in rendered for w in ("رم", "دیسک", "⚠", "ناموفق"))

    def test_refresh_never_crashes_on_a_broken_probe(self, tk_root: tk.Tk) -> None:
        from unittest import mock

        from universal_mind.system_status_tool import SystemStatusTool

        app = _app(tk_root)
        with mock.patch.object(SystemStatusTool, "status",
                               side_effect=RuntimeError("sensor died")):
            app._refresh_sysstatus()  # the tab names the failure, never crashes
        rendered = app._sys_text.get("1.0", tk.END)
        assert "ناموفق" in rendered
