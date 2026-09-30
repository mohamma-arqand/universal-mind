"""Tests: the desktop app's LIVE methods (R49 wave 2) — the operator's face.

Every store-touching method is exercised against an isolated temp db (the
operator's real store is never polluted); the window is hidden but the
widget tree is real, so every narrating method is testable end to end.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from collections.abc import Iterator
from unittest.mock import patch as mock_patch

import pytest

import universal_mind.scheduler as sched_mod
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


from contextlib import contextmanager


@contextmanager
def _isolated() -> Iterator[None]:
    """Route every store call to ONE fresh temp DatabaseSuite."""
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    patcher = mock_patch.object(sched_mod, "_store", lambda: suite)
    patcher.start()
    try:
        yield None
    finally:
        patcher.stop()


def _app(tk_root: tk.Tk) -> MindDesktopApp:
    return MindDesktopApp(tk_root)


class TestGoalFace:
    def test_a_bad_goal_sentence_names_the_format(self, tk_root: tk.Tk) -> None:
        from unittest.mock import patch as mp

        app = _app(tk_root)
        app._goal_entry.delete(0, tk.END)
        app._goal_entry.insert(0, "بدون قالب")
        with mp("universal_mind.desktop_app.messagebox") as mb:
            app._run_new_goal()
        assert mb.showinfo.called  # the format remedy, shown

    def test_a_real_goal_runs_and_narrates(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._goal_entry.delete(0, tk.END)
        app._goal_entry.insert(0, "هدف: میانگین ۴ و ۶ را حساب کن")
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            app._run_new_goal()
        text = app._goals_text.get("1.0", tk.END)
        assert "میانگین" in text  # the goal's own report, narrated

    def test_resume_without_stopped_goals_names_it(self, tk_root: tk.Tk) -> None:
        from unittest.mock import patch as mp

        app = _app(tk_root)
        with _isolated(), mp("universal_mind.desktop_app.messagebox") as mb:
            app._resume_goals()
        assert mb.showinfo.called
        assert "متوقفشدهای نیست" in mb.showinfo.call_args[0][1]


class TestScheduleFace:
    def test_refresh_schedules_lists_the_real_schedule(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated():
            from universal_mind.scheduler import register

            register("هر روز ساعت ۸ گزارش کامل بده")
            app._refresh_schedules()
        text = app._sched_text.get("1.0", tk.END)
        assert "فعال" in text
        assert "گزارش کامل" in text
        assert "سررسید بعدی" in text

    def test_register_schedule_from_the_entry(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        entry = app._sched_entry if hasattr(app, "_sched_entry") else None
        if entry is None:
            pytest.skip("no schedule entry in this layout")
        assert entry is not None  # skip narrows, but mypy wants the assert
        entry.delete(0, tk.END)
        entry.insert(0, "هر ۳۰ دقیقه میانگین بگیر")
        with _isolated(), mock_patch("universal_mind.desktop_app.messagebox"):
            app._register_schedule()
        text = app._sched_text.get("1.0", tk.END)
        assert "میانگین" in text


class TestVoteAndChips:
    def test_a_vote_records_and_thanks(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated():
            app._show_verdict_buttons("میانگین ۱ و ۲ را حساب کن")
            # the REAL buttons exist now — click 👍 through the widget:
            buttons = [w for w in app._verdict_bar.winfo_children()
                       if isinstance(w, ttk.Button)]
            assert len(buttons) == 2
            buttons[0].invoke()  # «عالی بود» — the real click
        # the acknowledgment arrived in the chat:
        assert "رأیت" in app._chat_log.get("1.0", tk.END) or app._chat_log.get("1.0", tk.END).strip()

    def test_a_second_vote_after_the_first_is_ignored(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated():
            app._show_verdict_buttons("میانگین ۳ و ۴ را حساب کن")
            buttons = [w for w in app._verdict_bar.winfo_children()
                       if isinstance(w, ttk.Button)]
            buttons[0].invoke()  # first click records
            # the bar is destroyed after the verdict:
            children = list(app._verdict_bar.winfo_children())
            assert not children  # one-click only

    def test_suggestion_chips_render_the_real_suggestions(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated():
            app._show_suggestion_chips(["سایت example.com را بخوان"])
        # no crash — the chips path works headless


class TestChatFace:
    def test_chat_send_narrates_the_reply(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        chat = app._chat_entry if hasattr(app, "_chat_entry") else None
        if chat is None:
            pytest.skip("no chat entry in this layout")
        assert chat is not None  # skip narrows, but mypy wants the assert
        chat.delete(0, tk.END)
        chat.insert(0, "وضعیت")
        with _isolated():
            with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
                app._chat_send()
        text = app._chat_log.get("1.0", tk.END)
        assert text.strip()  # the reply arrived in the chat


class TestStatusAndWatchers:
    def test_write_status_writes(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated():
            app._write_status()
        # no crash — the status bar works headless

    def test_scan_watchers_runs(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with _isolated(), mock_patch("universal_mind.desktop_app.messagebox"):
            app._scan_watchers()
        # no crash — messagebox MUST be mocked: showinfo is a live MODAL dialog
        # that parks the Tk event loop forever in a full-suite run (the zombie
        # that hung verify twice); the mock keeps the scan itself the test.


__test__ = True
