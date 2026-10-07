"""R79 B4 — WEATHER: real, cached, honestly labelled.

The old answer refused «هوا چطوره؟» while the machine was online.
Weather is now real: open-meteo live (no key), a shipped city gazetteer
(«هوای شیراز» resolves), a cache with an honest age label («از کشِ
۱۲ دقیقه پیش»), and a named refusal when neither live nor cache
exists — never a guess.
"""

from __future__ import annotations

import pytest


class TestTheWeatherCapability:
    def test_a_live_ask_answers_with_real_numbers(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("هوای تهران چطوره؟")
        assert p["route"] == ["weather"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert "درجه" in rep and ("زنده" in rep or "کش" in rep)

    def test_a_city_from_the_gazetteer(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("هوای شیراز چطوره؟")
        assert p.get("ok") is True
        assert "شیراز" in str(p.get("agent_report", ""))

    def test_bare_and_now_shapes_default_to_tehran(self) -> None:
        from universal_mind.persian_router import route_and_run

        for q in ("هوا؟", "هوا الان چطوره؟"):
            p = route_and_run(q)
            assert p.get("ok") is True, q
            assert "تهران" in str(p.get("agent_report", ""))

    def test_an_unknown_city_is_a_named_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("هوای زلمزو چطوره؟")
        assert p.get("ok") is False
        rep = str(p.get("agent_report", ""))
        assert "زلمزو" in rep and "فهرست" in rep

    def test_offline_with_a_sample_answers_from_cache_and_says_so(self) -> None:
        import universal_mind.weather_tool as wt

        live = wt.weather("تهران")  # warm the cache (or it already is)
        if live.get("ok") is not True:
            pytest.skip("no live sample to cache this run")
        real = wt.urllib.request.urlopen

        def _no_net(*_a, **_k):
            raise OSError("offline-proof")

        wt.urllib.request.urlopen = _no_net
        try:
            out = wt.weather("تهران")
            assert out["ok"] is True and out["source"] == "cache"
            assert "دقیقه پیش" in out["note"]
        finally:
            wt.urllib.request.urlopen = real

    def test_the_gazetteer_is_real_data(self) -> None:
        import json
        from pathlib import Path

        d = json.loads((Path(__file__).resolve().parents[1] / "data" /
                        "cities_fa.json").read_text(encoding="utf-8"))
        assert d["شیراز"] == [29.59, 52.58]
        assert len(d) >= 25
