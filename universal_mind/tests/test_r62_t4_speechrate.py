"""R62 T4 — speech accessibility: «کندتر/سریع‌تر حرف بزن» sets the pace.

The remembered SAPI rate (−10..+10) is a PREFERENCE: persisted once,
applied to every spoken run, listed in «تنظیماتت را نشان بده».
"""

from __future__ import annotations

import pytest

from universal_mind import operator_preferences as op
from universal_mind.reflexive import answer_reflexive


@pytest.fixture(autouse=True)
def _clean_rate():
    # the isolated store (R42): write, verify, and leave no trace
    op.set("speech_rate", "0")
    yield
    op.set("speech_rate", "0")


class TestTheSetting:
    def test_slower_steps_down_two(self) -> None:
        ans = answer_reflexive("کندتر حرف بزن")
        assert ans is not None
        assert int(op.get("speech_rate")) == -2
        assert "−۲" in ans["agent_report"] or "-۲" in ans["agent_report"]

    def test_faster_steps_up_two(self) -> None:
        op.set("speech_rate", "0")
        ans = answer_reflexive("سریع‌تر حرف بزن")
        assert ans is not None
        assert int(op.get("speech_rate")) == 2

    def test_the_floor_is_minus_ten(self) -> None:
        op.set("speech_rate", "-10")
        ans = answer_reflexive("کندتر حرف بزن")
        assert ans is not None
        assert int(op.get("speech_rate")) == -10

    def test_the_ceiling_is_ten(self) -> None:
        op.set("speech_rate", "10")
        ans = answer_reflexive("سریع‌تر حرف بزن")
        assert ans is not None
        assert int(op.get("speech_rate")) == 10

    def test_ahsitir_is_also_slower(self) -> None:
        op.set("speech_rate", "0")
        assert answer_reflexive("آهسته‌تر حرف بزن") is not None
        assert int(op.get("speech_rate")) == -2


class TestThePreferenceIsVisible:
    def test_the_settings_listing_shows_the_rate(self) -> None:
        op.set("speech_rate", "-4")
        from universal_mind.reflexive import answer_reflexive as ar

        rep = ar("تنظیماتت را نشان بده")["agent_report"]
        assert "speech_rate" in rep

    def test_the_answer_teaches_the_way_back(self) -> None:
        ans = answer_reflexive("کندتر حرف بزن")
        assert "سریع‌تر" in ans["agent_report"]


class TestTheConnectorAppliesIt:
    def test_the_rate_rides_into_speak(self) -> None:
        from universal_mind.speech_tool import SpeechTool, SpeechToolConnector

        class _Probe(SpeechTool):
            def __init__(self) -> None:
                super().__init__()
                self.seen_rate = 99

            def speak(self, text: str, *, voice_hint: str = "fa",
                      out_wav: str = "", rate: int = 0) -> dict[str, object]:
                self.seen_rate = rate
                return {"ok": True, "spoken": True, "voice": "(probe)", "text": text}

        probe = _Probe()
        out = SpeechToolConnector(tool=probe).connect(
            None, {"operation": "speak", "text": "سلام", "rate": -6})
        assert out.ok is True
        assert probe.seen_rate == -6

    def test_a_bad_rate_falls_back_to_default(self) -> None:
        from universal_mind.speech_tool import SpeechTool, SpeechToolConnector

        class _Probe(SpeechTool):
            def __init__(self) -> None:
                super().__init__()
                self.seen_rate = 99

            def speak(self, text: str, *, voice_hint: str = "fa",
                      out_wav: str = "", rate: int = 0) -> dict[str, object]:
                self.seen_rate = rate
                return {"ok": True, "spoken": True, "voice": "(probe)", "text": text}

        probe = _Probe()
        SpeechToolConnector(tool=probe).connect(
            None, {"operation": "speak", "text": "سلام", "rate": "نامعتبر"})
        assert probe.seen_rate == 0
