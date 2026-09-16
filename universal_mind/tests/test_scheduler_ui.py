"""Tests: the desktop schedules tab + the proactive tick."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def tk_root() -> Iterator[object]:
    """A hidden Tk root (skipped gracefully when no display exists)."""
    import tkinter as tk

    try:
        root = tk.Tk()
        root.withdraw()
    except Exception:
        pytest.skip("no display available for tkinter")
    yield root
    root.destroy()


class TestSchedulesTab:
    def test_tab_renders_the_real_schedule_table(self, tk_root: object) -> None:
        """The schedules tab renders persisted rows (or the honest empty)."""
        import tkinter as tk

        from universal_mind.desktop_app import MindDesktopApp

        app = MindDesktopApp(tk_root)  # type: ignore[arg-type]
        text = app._sched_text.get("1.0", tk.END)
        # either the honest empty message or real rows with the status line
        assert "زمانبندی" in text or "سررسید بعدی" in text

    def test_register_bad_syntax_shows_the_template(self, tk_root: object) -> None:
        """A bad sentence never registers; the honest template is shown."""
        from unittest.mock import patch as mock_patch

        import tkinter as tk

        from universal_mind.desktop_app import MindDesktopApp

        app = MindDesktopApp(tk_root)  # type: ignore[arg-type]
        app._sched_entry.delete(0, tk.END)
        app._sched_entry.insert(0, "شاید یه وقتی")
        with mock_patch("universal_mind.desktop_app.messagebox.showinfo") as info:
            app._register_schedule()
        info.assert_called_once()
        args = info.call_args.args
        assert "قالب" in str(args[-1])


class TestTick:
    def test_one_tick_is_idempotent(self) -> None:
        """Two immediate ticks: the second does not re-fire what just ran."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        first = tick()
        second = tick()
        fired_first = [f.get("command") for f in first.get("fired", [])]
        fired_second = [f.get("command") for f in second.get("fired", [])]
        repeat = [c for c in fired_second if c in fired_first]
        # only genuinely short-interval schedules could be due again instantly;
        # none were registered by this test, so nothing repeats
        assert repeat == [] or second["count"] == 0
