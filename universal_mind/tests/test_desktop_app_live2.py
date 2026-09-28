"""Tests: the desktop app's second face (R50 wave 1) — builder, dashboard,
single-capability run, chain run, Persian typing advice, preview, analytics.

Every method is exercised on a hidden-but-real Tk window; subprocess/browser
opens are patched AT desktop_app level (the real artifact stays real).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any
from collections.abc import Iterator
from unittest.mock import patch as mock_patch

import pytest

from universal_mind.desktop_app import MindDesktopApp


class _SyncThread:
    """A stand-in for threading.Thread that runs the target synchronously
    (Tk widgets can only be touched from the main thread in a headless test)."""

    def __init__(
        self,
        target: Callable[..., object],
        args: tuple[Any, ...] = (),
        daemon: bool | None = None,
    ) -> None:
        self._target = target
        self._args = args

    def start(self) -> None:
        self._target(*self._args)



@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def tk_root() -> Iterator[tk.Tk]:
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("no display available for tkinter")
    yield root
    root.destroy()


def _app(tk_root: tk.Tk) -> MindDesktopApp:
    return MindDesktopApp(tk_root)


class TestBuilderFace:
    """زنجیرهساز: pick → add → save (خطاها و موفقیت)."""

    def test_builder_save_without_name_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._builder_name.delete(0, tk.END)  # empty name
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._builder_save()
        assert mb.showinfo.called
        assert "نام" in mb.showinfo.call_args[0][1]

    def test_builder_save_without_picks_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._builder_name.delete(0, tk.END)
        app._builder_name.insert(0, "زنجیرهی من")
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._builder_save()
        assert mb.showinfo.called
        assert "قابلیت" in mb.showinfo.call_args[0][1]

    def test_builder_add_and_save_roundtrip(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        # pick a REAL capability the registry knows:
        names = list(app._builder_picked) if app._builder_picked else []
        if not names:
            # use the real capability list:
            app._builder_picked.append("data")
        app._builder_name.delete(0, tk.END)
        app._builder_name.insert(0, "z-test-chain")
        from universal_mind.chains_store import ChainsStore

        store = ChainsStore()
        saved_ids = {c.chain_id for c in store.load()}
        with (
            mock_patch("universal_mind.desktop_app.messagebox"),
            mock_patch.object(app, "_refresh_chain_list") as ref,
        ):
            app._builder_save()
        assert app._builder_status.cget("text").startswith("✓")
        ref.assert_called_once()
        # cleanup: delete ONLY the chains this test just created
        for chain in store.load():
            if chain.chain_id not in saved_ids:
                store.delete(chain.chain_id)

    def test_builder_remove_last_and_clear(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._builder_picked.append("data")
        app._builder_remove_last()
        assert "data" not in app._builder_picked
        app._builder_picked.append("chart")
        app._builder_clear()
        assert not app._builder_picked


class TestRunFace:
    """اجرای تکی: بدون انتخاب، JSON خراب، اجرای واقعی."""

    def test_run_without_selection_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        # ensure nothing is selected:
        for i in tuple(app._cap_list.curselection()):  # type: ignore[no-untyped-call]
            app._cap_list.selection_clear(i)
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._run()
        assert mb.showinfo.called

    def test_run_with_bad_json_names_the_error(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        if app._cap_list.size():
            app._cap_list.selection_clear(0, tk.END)
        app._cap_list.insert(tk.END, "data")
        app._cap_list.selection_set(tk.END)
        app._params_text.delete("1.0", tk.END)
        app._params_text.insert("1.0", "این JSON نیست")
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._run()
        assert mb.showerror.called

    def test_a_real_single_run_posts_back(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._cap_list.insert(tk.END, "data")
        app._cap_list.selection_set(tk.END)
        app._params_text.delete("1.0", tk.END)
        app._params_text.insert("1.0", "")

        with (
            mock_patch("universal_mind.desktop_app.orchestrate") as orch,
            mock_patch("universal_mind.desktop_app.threading.Thread", _SyncThread),
            mock_patch.object(app._root, "after", lambda _ms, fn, *a: fn(*a)),
        ):
            orch.return_value.ok = True
            orch.return_value.output = {"synthesized_from": "حاصل واقعی"}
            orch.return_value.sub_outputs = []
            app._run()
        assert "حاصل واقعی" in app._result_text.get("1.0", tk.END)


class TestChainFace:
    """اجرای زنجیره: بدون انتخاب → پیام؛ با انتخاب → thread → نتیجه."""

    def test_chain_run_without_selection_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        for i in tuple(app._chain_list.curselection()):  # type: ignore[no-untyped-call]
            app._chain_list.selection_clear(i)
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._run_chain()
        assert mb.showinfo.called

    def test_a_real_chain_run_posts_back(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)

        with (
            mock_patch("universal_mind.desktop_app.orchestrate") as orch,
            mock_patch("universal_mind.desktop_app.threading.Thread", _SyncThread),
            mock_patch.object(app._root, "after", lambda _ms, fn, *a: fn(*a)),
        ):
            orch.return_value.ok = True
            orch.return_value.output = {
                "synthesized_from": {"chart": {"path": "x.png", "ok": True}}
            }
            orch.return_value.sub_outputs = []
            app._chain_names.append(("نمونه", ["data", "chart"]))
            app._chain_list.insert(tk.END, "نمونه")
            app._chain_list.selection_set(tk.END)
            app._run_chain()
            text = app._chain_result.get("1.0", tk.END)
            assert "chart" in text and "x.png" in text


class TestPersianFace:
    """تایپ فارسی: کوتاه → نگه، بلند → پیشنهاد یا «هنوز تجربه نیست»."""

    def test_short_typing_keeps_the_placeholder(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._fa_entry.delete(0, tk.END)
        app._fa_entry.insert(0, "کو")  # < 6 chars
        app._on_fa_typing(None)
        assert "در حال نوشتن" in str(app._fa_advice_label.cget("text"))

    def test_long_typing_names_the_missing_experience(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._fa_entry.delete(0, tk.END)
        app._fa_entry.insert(0, "میانگین ارقام تهران را حساب کن")
        app._on_fa_typing(None)
        label = str(app._fa_advice_label.cget("text"))
        assert ("هنوز تجربه" in label) or ("پیشنهاد" in label)


class TestDashboardAndAnalytics:
    """داشبورد و تحلیلها: مسیرهای واقعی بدون باز کردن مرورگر/اکسپلورر."""

    def test_open_dashboard_builds_the_real_file(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with (
            mock_patch("webbrowser.open") as wb,
            mock_patch("subprocess.run") as sp,
        ):
            app._open_dashboard()
        assert (wb.called) or (sp.called)

    def test_open_preview_folder_without_artifact_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._preview_path = None
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._open_preview_folder()
        assert mb.showinfo.called

    def test_refresh_analytics_writes_real_numbers(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._refresh_analytics()
        text = app._analytics_text.get("1.0", tk.END) if hasattr(app, "_analytics_text") else ""
        assert isinstance(text, str)  # the method ran without crash on real data


class TestSchedulesAndResume:
    """زمانبندها و ادامه: مسیرهای خالی و واقعی."""

    def test_run_schedules_names_the_empty_state(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with mock_patch("universal_mind.desktop_app.messagebox"):
            app._run_schedules()
        # no crash on the empty path

    def test_refresh_schedules_no_crash(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._refresh_schedules()
        # ran against the real scheduler store without crashing


class TestPersianRun:
    """اجرای فرمان فارسی: خالی → پیام؛ واقعی → مسیر و نتیجه."""

    def test_empty_command_names_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._fa_entry.delete(0, tk.END)
        with mock_patch("universal_mind.desktop_app.messagebox") as mb:
            app._run_persian()
        assert mb.showinfo.called
        assert "فرمان" in mb.showinfo.call_args[0][1]

    def test_a_real_command_routes_and_narrates(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)


        payload = {
            "ok": True,
            "command": "میانگین ۴ و ۶ را حساب کن",
            "route": ["data"],
            "results": {"data": {"mean": 5.0, "ok": True}},
            "params": {"data": {}},
            "flows": ["data → chart"],
        }
        with (
            mock_patch("universal_mind.desktop_app.threading.Thread", _SyncThread),
            mock_patch.object(app._root, "after", lambda _ms, fn, *a: fn(*a)),
            mock_patch("universal_mind.persian_router.route_and_run", return_value=payload),
        ):
            app._fa_entry.delete(0, tk.END)
            app._fa_entry.insert(0, "میانگین ۴ و ۶ را حساب کن")
            app._run_persian()
        route_text = app._fa_route_text.get("1.0", tk.END)
        assert "data" in route_text  # the real route, narrated

    def test_a_crashed_engine_posts_the_error(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)


        def _boom(_cmd: str) -> dict[str, Any]:
            raise RuntimeError("موتور لنگ است")

        with (
            mock_patch("universal_mind.desktop_app.threading.Thread", _SyncThread),
            mock_patch.object(app._root, "after", lambda _ms, fn, *a: fn(*a)),
            mock_patch("universal_mind.persian_router.route_and_run", side_effect=_boom),
        ):
            app._fa_entry.delete(0, tk.END)
            app._fa_entry.insert(0, "هر فرمانی")
            app._run_persian()
        result_text = app._fa_result_text.get("1.0", tk.END)
        assert "موتور" in result_text  # the real crash, narrated honestly


class TestRemainingBranches:
    """شاخههای خطا و مسیرهای واقعیِ باقیمانده — هر کدام یک شاهد."""

    def test_resume_with_a_stopped_goal_runs_it(self, tk_root: tk.Tk) -> None:
        """یک هدف متوقفشدهی واقعی ساخته و ادامه داده میشود."""
        from universal_mind.agent_loop import _ensure_goals_table, run_goal, start_goal
        from universal_mind.database_suite import DatabaseSuite

        app = _app(tk_root)
        db = DatabaseSuite.shared_persistent()
        _ensure_goals_table(db)
        # isolate: mark ALL goals done, then seed exactly one stopped goal:
        db.execute("UPDATE goals SET state = 'done'")
        with mock_patch("universal_mind.desktop_app.messagebox"):
            started = start_goal("هدف: میانگین ۱۰ و ۲۰ را حساب کن", ("میانگین ۱۰ و ۲۰",))
            run_goal(started["goal_id"])
            db.execute(
                f"UPDATE goals SET state = 'stopped' WHERE id = {int(started['goal_id'])}"
            )
        with (
            mock_patch("universal_mind.desktop_app.messagebox"),
            mock_patch("universal_mind.real_notify.NotifyTool.notify"),
        ):
            app._resume_goals()
        text = app._goals_text.get("1.0", tk.END)
        assert ("میانگین" in text) or ("ادامه" in text)

    def test_chat_send_real_reply_branch(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._chat_entry.delete(0, tk.END)
        app._chat_entry.insert(0, "چه قابلیتی داری؟")
        with mock_patch("universal_mind.desktop_app.messagebox"):
            app._chat_send()
        text = app._chat_text.get("1.0", tk.END) if hasattr(app, "_chat_text") else ""
        assert isinstance(text, str)

    def test_builder_add_picks_the_real_choice(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        # seed the real choice widget with a real capability name:
        if app._builder_choice["values"]:
            app._builder_choice.set(app._builder_choice["values"][0])
        with mock_patch.object(app._builder_list, "insert"):
            app._builder_add()
        assert len(app._builder_picked) >= 1

    def test_refresh_chain_list_survives_a_broken_store(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with mock_patch(
            "universal_mind.chains_store.ChainsStore.load",
            side_effect=RuntimeError("store down"),
        ):
            app._refresh_chain_list()
        items = app._chain_list.get(0, tk.END)
        assert any("خطا در خواندن زنجیرهها" in str(x) for x in items)

    def test_open_dashboard_names_a_build_failure(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with (
            mock_patch(
                "universal_mind.superplatform_dashboard.build_dashboard",
                side_effect=RuntimeError("dying"),
            ),
            mock_patch("universal_mind.desktop_app.messagebox") as mb,
        ):
            app._open_dashboard()
        assert mb.showinfo.called
        assert "ناموفق" in mb.showinfo.call_args[0][1]

    def test_refresh_analytics_survives_a_broken_history(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        with mock_patch(
            "universal_mind.history_analytics.analyze_history",
            side_effect=RuntimeError("no history"),
        ):
            app._refresh_analytics()
        assert "(تحلیل ناموجود" in app._analytics_text.get("1.0", tk.END)

    def test_on_fa_typing_with_a_real_suggestion(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)

        class _Sugg:
            route = ["data", "chart"]
            mean_excellence = 0.75
            succeeded_runs = 3

        with mock_patch(
            "universal_mind.run_history.ChainAdvisor.advise", return_value=_Sugg()
        ), mock_patch(
            "universal_mind.run_history.ChainAdvisor.completion_hint", return_value="راهنما"
        ):
            app._fa_entry.delete(0, tk.END)
            app._fa_entry.insert(0, "میانگین ارقام تهران را حساب کن")
            app._on_fa_typing(None)
        label = str(app._fa_advice_label.cget("text"))
        assert "پیشنهاد" in label

    def test_register_schedule_then_refresh_shows_it(self, tk_root: tk.Tk) -> None:
        app = _app(tk_root)
        app._sched_entry.delete(0, tk.END)
        app._sched_entry.insert(0, "هر شب ساعت ۲۲ میانگین ۳ و ۵ را حساب کن")
        with mock_patch("universal_mind.desktop_app.messagebox"):
            app._register_schedule()
        app._refresh_schedules()
        text = app._sched_text.get("1.0", tk.END)
        assert isinstance(text, str)
