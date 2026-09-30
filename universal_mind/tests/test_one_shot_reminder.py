"""R53 wave-2 — THE ONE-SHOT REMINDER ENGINE, tested live.

«یادم بنداز که فردا زود بیدار شوم» used to be «نشناختم» — the single most
human reminder form. Now: a moment (فردا/امشب/ساعت H) parses to a LOCAL
run_at, persists as kind='once', fires ONCE (toast + speech under the mute
law), then the row self-deletes — a fired reminder that stays in the list
is a lie. Repeating schedules keep their exact old behavior (kind='').
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


def _clean_store() -> None:
    """Test against the REAL persistent store; only schedules rows are touched."""
    from universal_mind.scheduler import _ensure_table, _store

    db = _store()
    _ensure_table(db)
    db.execute("DELETE FROM schedules WHERE kind = 'once'")


class TestParseOneShot:
    def test_farda_saat_8_is_tomorrow_0800(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 14, 0)
        shot = parse_one_shot("یادم بنداز که فردا ساعت ۸ زود بیدار شوم", now)
        assert shot is not None
        fire = datetime.fromisoformat(shot["run_at"])
        assert fire == datetime(2026, 10, 1, 8, 0)

    def test_emshab_saat_21_is_today_evening(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 14, 0)
        shot = parse_one_shot("امشب ساعت ۲۱ دارو را بخور", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 9, 30, 21, 0)

    def test_bare_hour_in_the_past_means_tomorrow(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 15, 0)
        shot = parse_one_shot("یادم بنداز ساعت ۸ بیدارم کن", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 10, 1, 8, 0)

    def test_va_nim_half_past(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 10, 0)
        shot = parse_one_shot("فردا ساعت ۷ و نیم آب را روشن کن", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 10, 1, 7, 30)

    def test_pas_farda_two_days_out(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 10, 0)
        shot = parse_one_shot("پس‌فردا ساعت ۹ جلسه است", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 10, 2, 9, 0)

    def test_repeating_syntax_is_not_one_shot(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        assert parse_one_shot("هر ۳۰ دقیقه میانگین بگیر") is None
        assert parse_one_shot("هر روز ساعت ۸ گزارش بده") is None

    def test_farsi_digits_resolve(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 10, 0)
        shot = parse_one_shot("فردا ساعت ۱۵:۳۰ تماس دارم", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 10, 1, 15, 30)

    def test_bare_farda_means_morning_eight(self) -> None:
        from universal_mind.scheduler import parse_one_shot

        now = datetime(2026, 9, 30, 22, 0)
        shot = parse_one_shot("یادم بنداز فردا زود بیدار شوم", now)
        assert shot is not None
        assert datetime.fromisoformat(shot["run_at"]) == datetime(2026, 10, 1, 8, 0)


class TestOneShotLifecycle:
    def test_register_persists_once_row_with_run_at(self) -> None:
        from universal_mind.scheduler import list_schedules, register_one_shot

        _clean_store()
        res = register_one_shot("یادم بنداز که فردا ساعت ۸ زود بیدار شوم",
                                now=datetime.now())
        assert res["ok"] is True
        rows = [s for s in list_schedules() if s.kind == "once"]
        assert len(rows) == 1
        assert rows[0].run_at and rows[0].command
        _clean_store()

    def test_fire_once_then_self_delete(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The core law: fire (toast+speech) EXACTLY ONCE, then the row is GONE."""
        from universal_mind import scheduler as sched

        _clean_store()
        # A reminder due RIGHT NOW: run_at in the past.
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        db = sched._store()
        sched._ensure_table(db)
        db.insert_many("schedules", [{
            "command": "دارو را بخور", "every_minutes": "0", "hour_of_day": "-1",
            "minute_of_hour": "0", "last_run": "", "active": "1",
            "kind": "once", "run_at": past,
        }])
        monkeypatch.setattr("universal_mind.real_notify.NotifyTool.notify",
                            lambda self, t="", b="": {"ok": True, "shown": True})
        monkeypatch.setattr("universal_mind.speech_tool.SpeechTool.speak",
                            lambda self, text, **kw: {"ok": True, "spoken": True})
        out = sched.run_due(contest=False)
        once = [f for f in out.get("fired", []) if f.get("once")]
        assert len(once) == 1
        assert once[0]["command"] == "دارو را بخور"
        # THE LAW: the row self-deleted — a fired reminder is not in the list.
        assert not [s for s in sched.list_schedules() if s.kind == "once"]
        _clean_store()

    def test_future_one_shot_does_not_fire(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from universal_mind import scheduler as sched

        _clean_store()
        future = (datetime.now() + timedelta(hours=2)).isoformat()
        db = sched._store()
        sched._ensure_table(db)
        db.insert_many("schedules", [{
            "command": "قرار آینده", "every_minutes": "0", "hour_of_day": "-1",
            "minute_of_hour": "0", "last_run": "", "active": "1",
            "kind": "once", "run_at": future,
        }])
        out = sched.run_due(contest=False)
        assert not [f for f in out.get("fired", []) if f.get("once")]
        assert len([s for s in sched.list_schedules() if s.kind == "once"]) == 1
        _clean_store()

    def test_repeating_schedule_untouched_by_one_shot_law(self) -> None:
        """Back-compat: a pre-existing repeating row (kind='') still fires by interval."""
        from universal_mind.scheduler import Schedule, _next_due

        s = Schedule(schedule_id=1, command="x", every_minutes=30, hour_of_day=-1,
                     last_run=datetime.now().isoformat())
        assert _next_due(s) is not None  # interval logic unchanged


class TestRouterWiring:
    def test_yadam_bendaz_now_routes_to_scheduler_not_rejection(self) -> None:
        from universal_mind.persian_router import route_and_run

        _clean_store()
        res = route_and_run("یادم بنداز که فردا ساعت ۸ زود بیدار شوم")
        assert res["ok"] is True
        assert res["route"] == ["scheduler"]
        assert "یادآور یکبارمصرف" in res["agent_report"]
        _clean_store()

    def test_yadavarhayam_lists_real_rows(self) -> None:
        from universal_mind.persian_router import route_and_run

        _clean_store()
        route_and_run("یادم بنداز که فردا ساعت ۸ زود بیدار شوم")
        res = route_and_run("یادآورهای من")
        assert res["ok"] is True
        assert "زود بیدار شوم" in res["agent_report"]
        _clean_store()

    def test_delete_reminder_by_text(self) -> None:
        from universal_mind.persian_router import route_and_run

        _clean_store()
        route_and_run("یادم بنداز که فردا ساعت ۸ زود بیدار شوم")
        res = route_and_run("یادآور «زود بیدار شوم» را حذف کن")
        assert res["ok"] is True
        assert "حذف شد" in res["agent_report"]
        assert not [s for s in __import__("universal_mind.scheduler", fromlist=["x"]).list_schedules() if s.kind == "once"]
        _clean_store()

    def test_old_repeating_still_works(self) -> None:
        from universal_mind.persian_router import route_and_run

        _clean_store()
        res = route_and_run("یادآور کن هر ۳۰ دقیقه میانگین بگیر")
        assert res["ok"] is True
        assert "ثبت شد" in res["agent_report"]
        _clean_store()
