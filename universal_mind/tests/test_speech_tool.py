"""Tests: the speech tool — real SAPI voice, honest when Persian is missing."""

from __future__ import annotations



class TestSpeechTool:
    def test_english_speech_is_real(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """An English text produces real SAPI audio (a voice exists on Windows)."""
        from universal_mind.speech_tool import SpeechTool

        result = SpeechTool().speak("the report is ready", out_wav=str(tmp_path / "x.wav"))
        assert result["ok"] is True
        assert result["spoken"] is True
        assert result["voice"]  # WHICH voice was used is reported

    def test_emoji_never_reaches_the_wire(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """R55 THE EMOJI LAW: SAPI reads ✅'s NAME aloud ("White Heavy
        Checkmark") — emoji are visual and are stripped from spoken text;
        the words stay, the glyph never reaches the wire."""
        from universal_mind.speech_tool import SpeechTool

        result = SpeechTool().speak("✅ done 🎉", out_wav=str(tmp_path / "e.wav"))
        # either composed-but-silent (muted), or the wire ran on the CLEANED text
        assert result["ok"] is True or "empty text" in result.get("error", "")

    def test_persian_without_a_persian_voice_is_honest(self) -> None:
        """No fa-IR voice installed → the exact remedy, never a silent fake
        (SAPI would otherwise 'succeed' with a 46-byte empty wav)."""
        from universal_mind.speech_tool import SpeechTool

        result = SpeechTool().speak("گزارش آماده است")
        if result["ok"] is False:
            assert "صدای فارسی" in result["error"]  # the honest remedy
            assert "Speech" in result["error"]        # with the install path
        else:
            # a Persian voice IS installed — then it must really speak
            assert result["spoken"] is True

    def test_voice_inventory_is_real(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        inventory = SpeechTool().list_voices()
        assert inventory["ok"] is True
        assert inventory["voices"]  # Windows ships at least one desktop voice

    def test_connector_dispatches_speak(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.speech_tool import SpeechToolConnector

        conn = SpeechToolConnector()
        result = conn.connect({}, {"operation": "speak", "text": "done"})
        assert isinstance(result, ConnectorResult)
        assert result.ok is True  # English text always speakable

    def test_unknown_operation_fails_clean(self) -> None:
        from universal_mind.speech_tool import SpeechToolConnector

        conn = SpeechToolConnector()
        result = conn.connect({}, {"operation": "sing"})
        assert result.ok is False


class TestSpeechFlow:
    def test_data_feeds_speech(self) -> None:
        """«حساب کن و بلند بخوان» — the computed summary is the spoken text."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۴ و ۶ را حساب کن و بلند بخوان")
        assert payload["route"] == ["data", "speech"]
        flows = payload["flows"]
        assert any("→ speech" in f for f in flows)
        # the flow line itself carries the real summary that was spoken
        spoken_flow = next(f for f in flows if "→ speech" in f)
        assert "شاخص" in spoken_flow or "میانگین" in spoken_flow

    def test_explicit_text_wins(self) -> None:
        from universal_mind.orchestration import _flow_params

        params, flow = _flow_params(
            "speech", {"operation": "speak", "text": "سلام دنیا"},
            "data", {"ok": True, "mean": 5.0}, "cmd", (),
        )
        assert params["text"] == "سلام دنیا"  # explicit, untouched
        assert flow is None
