"""Tests: R44 item 9 — the EARS (real speech-to-text as an operator gesture).

Live laws:
1. `listen()` is honest: a missing engine names the remedy, silence says so,
   a real phrase returns the recognized text.
2. «گوش کن» is an operator GESTURE routed through the hearing class — never
   a capability run, never shadowed by vocabulary.
3. The echo comes FIRST: the routed command's answer is prefixed with
   «شنیدم: «...»» — a misheard command is never executed silently.
"""

from __future__ import annotations

from typing import Any


class TestListenHonesty:
    """SpeechTool.listen — the real STT surface, honestly shaped."""

    def test_missing_engine_names_the_remedy(self) -> None:
        from unittest.mock import patch as mock_patch

        from universal_mind.speech_tool import SpeechTool

        class _Proc:
            stdout = "NO_ENGINE"
            stderr = ""
            returncode = 0

        with mock_patch("universal_mind.speech_tool.subprocess.run", return_value=_Proc()):
            out = SpeechTool().listen(seconds=2)
        assert out["ok"] is False
        assert "Settings" in out["error"] and out["recognized"] == ""

    def test_silence_is_honest(self) -> None:
        from unittest.mock import patch as mock_patch

        from universal_mind.speech_tool import SpeechTool

        class _Proc:
            stdout = "TEXT:"
            stderr = ""
            returncode = 0

        with mock_patch("universal_mind.speech_tool.subprocess.run", return_value=_Proc()):
            out = SpeechTool().listen(seconds=2)
        assert out["ok"] is True
        assert out["recognized"] == ""
        assert "شنیده نشد" in out["note"]

    def test_a_heard_phrase_rides_back(self) -> None:
        from unittest.mock import patch as mock_patch

        from universal_mind.speech_tool import SpeechTool

        class _Proc:
            stdout = "TEXT:chart the numbers"
            stderr = ""
            returncode = 0

        with mock_patch("universal_mind.speech_tool.subprocess.run", return_value=_Proc()):
            out = SpeechTool().listen(seconds=2)
        assert out["ok"] is True
        assert out["recognized"] == "chart the numbers"


class TestTheHearingGesture:
    """is_hearing_phrase + hear_and_run — the echo-then-act contract."""

    def test_only_real_gestures_match(self) -> None:
        from universal_mind.hearing import is_hearing_phrase

        assert is_hearing_phrase("گوش کن") is True
        assert is_hearing_phrase("گوش بده") is True
        assert is_hearing_phrase("به من گوش کن") is True
        assert is_hearing_phrase("نمودار بکش") is False
        assert is_hearing_phrase("") is False

    def test_heard_text_is_echoed_then_routed(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-9.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            with mock_patch(
                "universal_mind.speech_tool.SpeechTool.listen",
                return_value={"ok": True, "recognized": "میانگین ۴ و ۶ را حساب کن",
                              "lang": "fa-IR", "seconds": 5, "note": "", "error": ""},
            ):
                from universal_mind.hearing import hear_and_run

                p: Any = hear_and_run(5)
        assert p["ok"] is True
        assert p["heard"] == "میانگین ۴ و ۶ را حساب کن"
        assert "شنیدم" in p["agent_report"]
        assert p["route"] == ["data"]  # the heard command really ran

    def test_engine_failure_never_invents_work(self) -> None:
        from unittest.mock import patch as mock_patch

        with mock_patch(
            "universal_mind.speech_tool.SpeechTool.listen",
            return_value={"ok": False, "recognized": "", "error": "میکروفون نیست"},
        ):
            from universal_mind.hearing import hear_and_run

            p = hear_and_run(5)
        assert p["ok"] is False
        assert "نشنیدم" in p["agent_report"]
        assert p["route"] == ["speech"]

    def test_the_router_routes_the_gesture(self) -> None:
        """«گوش کن» reaches the hearing class — not the speak vocabulary."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-9b.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            with mock_patch(
                "universal_mind.speech_tool.SpeechTool.listen",
                return_value={"ok": True, "recognized": "میانگین ۲ و ۸ را حساب کن",
                              "lang": "fa-IR", "seconds": 5, "note": "", "error": ""},
            ):
                from universal_mind.persian_router import route_and_run

                p = route_and_run("گوش کن")
        assert p["heard"] == "میانگین ۲ و ۸ را حساب کن"
        assert p["route"] == ["data"]
        assert "شنیدم" in p["agent_report"]
