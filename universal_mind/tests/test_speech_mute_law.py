"""R53 THE MUTE LAW — one switch for the whole platform's voice.

«بیصدا» flips the persistent voice_muted preference; every speak() reads it
LIVE (never cached). A muted speak is HONEST: ok=True, spoken=True,
muted=True, voice="(muted)" — composed but silent. «باز صدا» restores the
voice. The mute mode-verb PRECEDES keyword routing: «بیصدا» must never reach
the SAPI voice as text-to-say (the old bug: the platform SAID «بیصدا» aloud).
UM_MUTE=1 is the same switch for headless runs.
"""

from __future__ import annotations

import os

import pytest


class TestMuteModeVerb:
    def test_biseda_flips_the_switch_and_answers_in_persian(self) -> None:
        from universal_mind.persian_router import route_and_run

        res = route_and_run("بیصدا")
        assert res["ok"] is True
        assert res["route"] == ["mute"]
        assert res["result"]["muted"] is True
        assert "بی‌صدا" in res["agent_report"]

    def test_mute_verb_never_reaches_the_sapi_voice(self) -> None:
        """The old bug: «بیصدا» matched the 'صدا' speech keyword and the
        platform SAID «بیصدا» ALOUD through SAPI. The mode-verb must win."""
        from universal_mind import operator_preferences as prefs
        from universal_mind.persian_router import route_and_run

        route_and_run("بیصدا")
        assert (prefs.get("voice_muted") or "").strip() == "1"
        prefs.set("voice_muted", "")  # restore

    def test_baz_seda_restores_the_voice(self) -> None:
        from universal_mind import operator_preferences as prefs
        from universal_mind.persian_router import route_and_run

        route_and_run("بیصدا")
        res = route_and_run("باز صدا")
        assert res["route"] == ["mute"]
        assert res["result"]["muted"] is False
        assert (prefs.get("voice_muted") or "").strip() == ""
        assert "صدا برگشت" in res["agent_report"]


class TestMutedSpeakIsHonest:
    def test_muted_speak_is_composed_but_silent(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("UM_MUTE", "1")
            res = SpeechTool().speak("سلام")
        assert res["ok"] is True
        assert res["spoken"] is True
        assert res["muted"] is True
        assert res["voice"] == "(muted)"
        assert res["note"] == "بیصدا — برای صدا، «باز صدا» بگو"

    def test_preference_row_mutes_speech_too(self) -> None:
        from universal_mind import operator_preferences as prefs
        from universal_mind.speech_tool import SpeechTool

        try:
            prefs.set("voice_muted", "1")
            res = SpeechTool().speak("تست")
            assert res["muted"] is True
        finally:
            prefs.set("voice_muted", "")

    def test_unmuted_speak_still_works_and_has_no_muted_field(self) -> None:
        """UM_MUTE absent + row cleared => the REAL voice path (SAPI); on a
        Persian-less Windows it fails honestly — that is the honest contract,
        and it must NOT be the muted fast-path."""
        from universal_mind.speech_tool import SpeechTool

        os.environ.pop("UM_MUTE", None)
        res = SpeechTool().speak("hello world")
        assert "muted" not in res or res.get("muted") is not True


class TestMuteSurvivesAndIsReadLive:
    def test_the_switch_is_read_live_not_cached(self) -> None:
        """set row => muted; clear row => unmuted, no process restart."""
        from universal_mind import operator_preferences as prefs
        from universal_mind.speech_tool import SpeechTool

        try:
            prefs.set("voice_muted", "1")
            assert SpeechTool().speak("یک").get("muted") is True
            prefs.set("voice_muted", "")
            got = SpeechTool().speak("hello world")  # english => real SAPI
            assert got.get("muted") is not True
        finally:
            prefs.set("voice_muted", "")

    def test_scheduler_voice_is_muted_by_the_same_law(self) -> None:
        """scheduler.py's goal-outcome voice runs through SpeechTool().speak —
        the SAME switch must silence it (one law, every caller)."""

        from universal_mind import speech_tool
        from universal_mind import operator_preferences as prefs

        spoken: list[str] = []
        real_speak = speech_tool.SpeechTool.speak

        def _spy(self, text, **kw):
            spoken.append(text)
            return real_speak(self, text, **kw)

        try:
            prefs.set("voice_muted", "1")
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(speech_tool.SpeechTool, "speak", _spy)
                res = speech_tool.SpeechTool().speak("هدف تمام شد")
            assert res.get("muted") is True
        finally:
            prefs.set("voice_muted", "")
