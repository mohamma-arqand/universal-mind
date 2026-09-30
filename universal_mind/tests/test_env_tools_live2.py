"""Tests: the environment-bound tools' LIVE branches (R51 wave 2).

Speech talks to the REAL Windows SAPI (PowerShell System.Speech); email
sends against a local SMTP stub (no external network); every honest
refusal branch is named.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

import pytest


class TestSpeechLive:
    """SAPI واقعی ویندوز: لیست صداها، صداقت صدای فارسی، مسیرهای خطا.

    R53+THE PERMANENT MUTE: these tests exercise the REAL voice wire (a
    missing engine, a failing engine, a broken wav) — the mute law would
    short-circuit speak() before the wire is ever touched and the honest
    failures under test would never happen. So the class LIFTS the mute
    for its own duration and RESTORES the operator's permanent choice
    (voice_muted='1') in teardown — the mute is the platform's law, and
    these tests are the voice's own physical.
    """

    @pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
    def _unmute_for_the_real_wire(self) -> Iterator[None]:
        from universal_mind import operator_preferences as prefs

        was = (prefs.get("voice_muted") or "").strip()
        prefs.set("voice_muted", "")
        yield
        prefs.set("voice_muted", was or "1")  # restore the permanent choice

    def test_list_voices_is_real(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        r = SpeechTool().list_voices()
        assert r["ok"] is True  # a real Windows has at least one voice
        assert len(r["voices"]) >= 1

    def test_empty_text_is_refused(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        r = SpeechTool().speak("")
        assert r["ok"] is False
        assert r["error"] == "empty text"

    def test_a_missing_powershell_is_named(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        with mock_patch(
            "universal_mind.speech_tool.subprocess.run",
            side_effect=FileNotFoundError("no powershell"),
        ):
            r = SpeechTool().speak("سلام")
        assert r["ok"] is False
        assert "no powershell" in r["error"]

    def test_a_failing_engine_is_named(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        class _Bad:
            returncode = 1
            stdout = ""
            stderr = "engine broke"

        with mock_patch(
            "universal_mind.speech_tool.subprocess.run", return_value=_Bad()
        ):
            r = SpeechTool().speak("hello")
        assert r["ok"] is False
        assert "engine broke" in r["error"]

    def test_english_speaks_and_names_the_voice(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        r = SpeechTool().speak("hello world")
        assert r["ok"] is True
        assert r["voice"]  # WHICH voice, named — never silent

    def test_persian_without_a_farsi_voice_is_honest(self) -> None:
        """اگر صدای فارسی نصب نباشد، صادقانه نامیده میشود؛ اگر هست، راست میگوید."""
        from universal_mind.speech_tool import SpeechTool

        r = SpeechTool().speak("سلام دنیا")
        voices = SpeechTool().list_voices()
        has_fa = any(
            tag in str(v).lower() for v in voices["voices"] for tag in ("fa-", "farsi", "persian", "ar-")
        )
        assert r["ok"] == has_fa  # the honest law, both ways

    def test_wav_output_makes_a_real_file(self, tmp_path: Path) -> None:
        from universal_mind.speech_tool import SpeechTool

        wav = tmp_path / "out.wav"
        r = SpeechTool().speak("hello", out_wav=str(wav))
        assert r["ok"] is True
        assert wav.exists() and wav.stat().st_size > 0
        assert r["bytes"] == wav.stat().st_size

    def test_a_broken_wav_is_named(self, tmp_path: Path) -> None:
        from universal_mind.speech_tool import SpeechTool

        class _Fake:
            returncode = 0
            stdout = "SPOKEN:Microsoft David"
            stderr = ""

        with mock_patch(
            "universal_mind.speech_tool.subprocess.run", return_value=_Fake()
        ):
            r = SpeechTool().speak("hello", out_wav=str(tmp_path / "ghost.wav"))
        assert r["ok"] is False
        assert "wav was not produced" in r["error"]

    def test_a_listening_engine_failure_is_named(self) -> None:
        from universal_mind.speech_tool import SpeechTool

        with mock_patch(
            "universal_mind.speech_tool.subprocess.run",
            side_effect=OSError("no engine"),
        ):
            r = SpeechTool().listen(seconds=1)
        assert r["ok"] is False
        assert "در دسترس نیست" in r["error"]

    def test_listen_timeout_is_named(self) -> None:
        import subprocess as sp

        from universal_mind.speech_tool import SpeechTool

        with mock_patch(
            "universal_mind.speech_tool.subprocess.run",
            side_effect=sp.TimeoutExpired(cmd="x", timeout=1),
        ):
            r = SpeechTool().listen(seconds=1)
        assert r["ok"] is False
        assert "طول کشید" in r["error"]


class TestEmailSmtpLive:
    """ایمیل: سیمِ واقعی به پورتِ بسته → خطای صادقانه؛ compose موفق قبلاً پوشش داده."""

    def test_a_dead_wire_is_named_honestly(self, tmp_path: Path) -> None:
        import os

        from universal_mind.email_outbox import compose, send

        # port 1 on localhost: nothing listens — a REAL refused connection
        eml = compose(to="dest@example.com", subject="تست", body="متن", out_dir=str(tmp_path))
        os.environ["UM_SMTP_HOST"] = "127.0.0.1"
        os.environ["UM_SMTP_PORT"] = "1"
        try:
            r = send(eml["path"])
        finally:
            os.environ.pop("UM_SMTP_HOST", None)
            os.environ.pop("UM_SMTP_PORT", None)
        assert r["ok"] is False
        assert r["sent"] is False
        assert "ارسال ناموفق" in r["error"]  # the real exception, named not hidden

    def test_a_starttls_refusal_is_named(self, tmp_path: Path) -> None:
        import os
        import socket

        from universal_mind.email_outbox import compose, send

        received: list[Any] = []

        # a minimal plain SMTP stub that ADVERTISES no STARTTLS-READY TLS:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)
        srv.settimeout(5)

        def handle() -> None:
            try:
                conn, _ = srv.accept()
                f = conn.makefile("rwb")

                def send_line(line: str) -> None:
                    conn.sendall((line + "\r\n").encode())

                send_line("220 stub")
                data_mode = False
                msg: list[Any] = []
                while True:
                    line = f.readline()
                    if not line:
                        break
                    txt = line.decode(errors="replace").strip()
                    if data_mode:
                        if txt == ".":
                            data_mode = False
                            received.append(b"\n".join(msg))
                            send_line("250 ok")
                        else:
                            msg.append(line.rstrip(b"\r\n"))
                        continue
                    cmd = txt.split()[0].upper() if txt else ""
                    if cmd == "STARTTLS":
                        send_line("454 TLS not available")  # honest refusal
                    elif cmd == "DATA":
                        send_line("354 go")
                        data_mode = True
                    elif cmd == "QUIT":
                        send_line("221 bye")
                        break
                    else:
                        send_line("250 ok")
                conn.close()
            except OSError:
                pass

        t = threading.Thread(target=handle)
        t.daemon = True
        t.start()
        try:
            eml = compose(to="dest@example.com", subject="تست", body="متن", out_dir=str(tmp_path))
            os.environ["UM_SMTP_HOST"] = "127.0.0.1"
            os.environ["UM_SMTP_PORT"] = str(port)
            try:
                r = send(eml["path"])
            finally:
                os.environ.pop("UM_SMTP_HOST", None)
                os.environ.pop("UM_SMTP_PORT", None)
            assert r["ok"] is False
            assert "STARTTLS" in r["error"] or "ارسال ناموفق" in r["error"]
        finally:
            srv.close()
            t.join(timeout=2)
