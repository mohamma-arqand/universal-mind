"""R79 A1-A5 — the FALSE-SUCCESS wave.

The live product audit found the honesty law's next frontier: five
commands claimed success while nothing real happened. A claimed success
with nothing changed is the worst lie.

- A1 «صدا را بلندتر کن»: speech only TALKED; the real master volume
  never moved. Now the volume sentences drive the compiled WASAPI
  helper (tools/volctl.exe) and report the MEASURED before:after; a
  muted endpoint is unmuted first (and that is NAMED).
- A2 «موسیقی پخش کن» produced a 147-byte PNG. Media has no player:
  the ask is a NAMED refusal with the real path (open the file in the
  default player).
- A3 «ویروس اسکن کن» went to image processing. Security scanning is
  Windows Defender's job: a NAMED refusal that offers to open it.
- A4 «رم را آزاد کن» only REPORTED vitals. Now the real act (a
  working-set trim) runs and the MEASURED before:after is reported —
  including the honest «nothing meaningful changed» when Windows
  manages its own cache.
- A5 «شعر بگو»/«شوخی کن» spoke a fixed sentence. Real creativity needs
  a live model: a NAMED refusal, never a fake poem.
"""

from __future__ import annotations



class TestTheRealVolume:
    def test_up_and_set_move_the_measured_volume(self) -> None:
        from universal_mind.volume_tool import get_volume, set_volume

        v0 = get_volume()
        assert v0["ok"] is True, v0.get("error")
        s = set_volume(delta=0.05)
        assert s["ok"] is True and s["after"] != v0["volume"] or s["changed"] is False
        set_volume(level=v0["volume"] / 100.0)  # restore
        v1 = get_volume()
        assert v1["volume"] == v0["volume"]

    def test_the_volume_sentences_route_sysstatus_not_speech(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("صدا را بلندتر کن")
        assert p["route"] == ["sysstatus"], p["route"]
        assert "ولوم واقعی" in str(p.get("agent_report", ""))

    def test_a_volume_query_answers_the_measured_level(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("ولوم چند است؟")
        assert p["ok"] is True and "ولوم الان" in str(p.get("agent_report", ""))


class TestTheNamedRefusals:
    def test_a_play_ask_names_the_missing_player(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یه موسیقی قشنگ پخش کن")
        assert p["ok"] is False
        rep = str(p.get("agent_report", ""))
        assert "پخشکنندهٔ واقعی ندارم" in rep and "باز کن" in rep

    def test_a_virus_scan_names_defender(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("ویروس اسکن کن")
        assert p["ok"] is False
        rep = str(p.get("agent_report", ""))
        assert "Defender" in rep and "باز کن" in rep

    def test_a_poem_ask_never_recites_a_fixed_line(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("شعر بگو درباره باران")
        assert p["ok"] is False
        rep = str(p.get("agent_report", ""))
        assert "خلاقیت" in rep and "نمیگویم" in rep

    def test_a_joke_ask_is_the_same_honest_class(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("برام شوخی کن")
        assert p["ok"] is False and "خلاقیت" in str(p.get("agent_report", ""))


class TestTheRealRamAct:
    def test_free_ram_reports_the_measured_before_after(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("رم را آزاد کن")
        assert p["route"] == ["sysstatus"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert ("رم واقعاً آزاد شد" in rep) or ("تغییر نکرد" in rep)

    def test_plain_status_still_reports(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("وضعیت سیستم را بگو")
        assert p["ok"] is True and "رم" in str(p.get("agent_report", ""))
