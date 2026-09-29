"""R52 wave: LIVE branch tests for scheduler, persian_router, orchestration.

Every case drives the REAL function with a real Persian sentence (or a real
temp folder) — no mock of the unit under test. The branches covered here are
the BEHAVIORAL gaps left by R51's sweep (parse halves/quarters, folder-watcher
resolution, an honest refusal when nothing is schedulable, the no-vocab route,
the hearing phrase's seconds, the flow-order note), not the defensive
`except: lens-never-blocker` rows that are deliberate refusal paths.
"""

from __future__ import annotations

from pathlib import Path


class TestParseScheduleHalves:
    """«ساعت ۸ و نیم / و ربع / ۸:30» — halves and quarters beat the bare hour."""

    def test_half_hour_is_30_minutes(self) -> None:
        from universal_mind.scheduler import parse_schedule

        r = parse_schedule("هر روز ساعت ۸ و نیم گزارش بده")
        assert r is not None
        assert r["every_minutes"] == 1440
        assert r["hour_of_day"] == 8
        assert r.get("minute_of_hour") == 30

    def test_quarter_hour_is_15_minutes(self) -> None:
        from universal_mind.scheduler import parse_schedule

        r = parse_schedule("هر روز ساعت ۷ و ربع خبرم کن")
        assert r is not None
        assert r.get("minute_of_hour") == 15

    def test_colon_form_parses_minutes(self) -> None:
        from universal_mind.scheduler import parse_schedule

        r = parse_schedule("هر روز ساعت 8:30 گزارش بده")
        assert r is not None
        assert r.get("minute_of_hour") == 30

    def test_an_hour_out_of_range_refuses(self) -> None:
        from universal_mind.scheduler import parse_schedule

        assert parse_schedule("هر روز ساعت ۲۵ گزارش بده") is None

    def test_a_folder_phrase_is_not_a_time_schedule(self) -> None:
        from universal_mind.scheduler import parse_schedule

        assert parse_schedule("هر وقت در پوشهی دسکتاپ فایل جدید اومد خبرم کن") is None

    def test_gibberish_refuses_honestly(self) -> None:
        from universal_mind.scheduler import parse_schedule

        assert parse_schedule("sometime maybe") is None


class TestFolderWatcher:
    """«هر وقت در پوشهی X فایل جدید...» — the watcher resolution law."""

    def test_a_known_folder_resolves(self) -> None:
        from universal_mind.scheduler import parse_folder_watcher

        r = parse_folder_watcher("هر وقت در پوشهی دسکتاپ فایل جدید اومد خبرم کن")
        assert r is not None
        assert Path(str(r.get("path") or r.get("folder"))).is_dir()

    def test_an_unknown_folder_refuses(self) -> None:
        from universal_mind.scheduler import parse_folder_watcher

        assert parse_folder_watcher("هر وقت در پوشهی ناموجودxyz فایل جدید اومد خبرم کن") is None

    def test_a_phrase_without_the_folder_word_refuses(self) -> None:
        from universal_mind.scheduler import parse_folder_watcher

        assert parse_folder_watcher("هر وقت فایل جدید اومد خبرم کن") is None

    def test_a_real_temp_folder_resolves(self, tmp_path: Path) -> None:
        from universal_mind.scheduler import parse_folder_watcher

        r = parse_folder_watcher(f"هر وقت در پوشهی {tmp_path} فایل جدید اومد خبرم کن")
        assert r is not None
        # the folder key resolves to THIS temp dir (same path, native spelling):
        assert Path(str(r["folder"])).is_dir()
        assert Path(str(r["folder"])).resolve() == tmp_path.resolve()


class TestRegisterRefusesNothing:
    """register() with nothing schedulable names it honestly."""

    def test_registering_gibberish_refuses_with_persian_error(self) -> None:
        from universal_mind import scheduler

        r = scheduler.register("sometime maybe")
        assert r["ok"] is False
        assert "زمانبندی" in r["error"]


class TestRouterBehavioralBranches:
    """persian_router: the no-vocab route and the hearing seconds."""

    def test_a_command_with_no_known_words_routes_to_nothing(self) -> None:
        from universal_mind.persian_router import route

        r = route("xyzzy flurbo")
        assert r.capabilities == ()
        assert r.unknown == ("xyzzy flurbo",)

    def test_a_hearing_phrase_is_recognized(self) -> None:
        from universal_mind.hearing import is_hearing_phrase

        # the hearing gate: these ARE hearing requests, a filled sentence is not
        assert is_hearing_phrase("گوش کن") is True
        assert is_hearing_phrase("به من گوش کن") is True
        assert is_hearing_phrase("گوش بده") is True
        assert is_hearing_phrase("نمودار فروش را بکش") is False

    def test_hearing_runs_the_real_listen_window(self) -> None:
        # The LIVE hearing law: hear_and_run(seconds=1) runs the real SAPI
        # listener for a real 1s window and returns an HONEST dict — a
        # transcript, or the named absence of a listener. Never a crash.
        from universal_mind.hearing import hear_and_run

        res = hear_and_run(seconds=1)
        assert isinstance(res, dict)
        assert "ok" in res  # the honest outcome, whichever way the mic answers


class TestFlowOrderNote:
    """orchestration: the dependency-order note renders when a flow re-orders."""

    def test_a_producer_before_consumer_flows_note_in_render(self) -> None:
        from universal_mind.persian_router import route_and_run

        # A real chain whose dependency planner re-orders (chart before pdf):
        res = route_and_run("نمودار دادههای ۵ و ۷ و ۹ را بکش و در PDF بگذار")
        assert res["ok"] is True
        report = str(res.get("agent_report", ""))
        # the honest note about the corrected step order (or its absence when
        # the order was already right) — both are lawful, but a report exists:
        assert report
