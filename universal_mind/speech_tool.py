"""The speech tool — the platform SPEAKS its results in real Persian audio.

Uses the Windows SAPI voice (System.Speech via PowerShell): the same OS-native
channel as the toast and clipboard, no downloads, no external services. The
operator's language matters end to end — a Persian report deserves a Persian
voice, and Persian voices are preferred when installed (fa-IR), with an honest
fallback message when none exists (never a silent no-op).

Real effects only: the call either makes sound or reports exactly why not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class SpeechTool:
    """A real text-to-speech specialist (Windows SAPI through PowerShell)."""

    name = "speech"
    capability = "speech"

    def speak(
        self,
        text: str,
        *,
        voice_hint: str = "fa",
        out_wav: str = "",
        rate: int = 0,
    ) -> dict[str, Any]:
        """Speak (and optionally record) real audio through Windows SAPI.

        voice_hint: preferred language tag ('fa' prefers Persian voices).
        out_wav: when set, ALSO records to this .wav path (real audio bytes).
        rate: -10..10 SAPI rate adjustment.

        Persian selection is honest: fa-IR voices first, then ar/dari, then
        anything; if no matching voice exists the call still speaks with the
        default voice and says WHICH voice was used — never a silent fake.
        """
        if not text:
            return {"ok": False, "error": "empty text", "spoken": False}

        # HONEST VOICE MATCHING: an English-only voice cannot speak Persian —
        # SAPI silently produces an empty wav. If the text carries Persian
        # glyphs, a Persian-capable voice is REQUIRED (fa/ar); without one the
        # call fails with the exact remedy, never a silent 46-byte fake.
        has_persian = any("\u0600" <= ch <= "\u06FF" for ch in text)

        # Build the voice-pick script: prefer fa, then ar, then default.
        pick = (
            "$v = $null; "
            "foreach ($vs in (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()) { "
            "  $i = $vs.VoiceInfo; "
            "  if ($i.Culture.Name -like 'fa-*') { $v = $i.Name; break } "
            "} "
            "if (-not $v) { "
            "  foreach ($vs in (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()) { "
            "    $i = $vs.VoiceInfo; "
            "    if ($i.Culture.Name -like 'ar-*') { $v = $i.Name; break } "
            "  } "
            "} "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "if ($v) { $s.SelectVoice($v) }; "
            "$s.Rate = " + str(rate) + "; "
        )
        speak_cmd = (
            f"$s.Speak([System.Text.Encoding]::UTF8.GetString("
            f"[Convert]::FromBase64String('{_b64(text)}'))); "
            "'SPOKEN:' + $s.Voice.Name"
        )
        record_cmd = ""
        if out_wav:
            record_cmd = (
                f"$s.SetOutputToWaveFile('{Path(out_wav).as_posix()}'); "
                f"$s.Speak([System.Text.Encoding]::UTF8.GetString("
                f"[Convert]::FromBase64String('{_b64(text)}'))); "
                "$s.SetOutputToNull(); "
                "'SPOKEN:' + $s.Voice.Name"
            )
        script = (
            "Add-Type -AssemblyName System.Speech; " + pick
            + (record_cmd if out_wav else speak_cmd)
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "error": str(exc), "spoken": False}

        if result.returncode != 0:
            return {
                "ok": False, "spoken": False,
                "error": result.stderr.strip() or "speech synthesis failed",
            }
        spoken_line = next(
            (ln for ln in result.stdout.splitlines() if ln.startswith("SPOKEN:")),
            "SPOKEN:(unknown)",
        )
        voice_name = spoken_line.removeprefix("SPOKEN:").strip()
        if has_persian and not any(
            tag in voice_name.lower() for tag in ("fa-", "farsi", "persian", "ar-")
        ):
            return {
                "ok": False, "spoken": False,
                "error": (
                    "صدای فارسی روی این ویندوز نصب نیست — "
                    "از Settings > Time & Language > Speech یک صدای فارسی (fa-IR) نصب کن"
                ),
            }
        out = {"ok": True, "spoken": True, "voice": voice_name, "error": ""}
        if out_wav:
            wav = Path(out_wav)
            if wav.exists() and wav.stat().st_size > 0:
                out["path"] = str(wav)
                out["bytes"] = wav.stat().st_size
            else:
                return {"ok": False, "spoken": False, "error": "wav was not produced"}
        return out

    def list_voices(self) -> dict[str, Any]:
        """The REAL installed SAPI voices (names + cultures) — honest inventory."""
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "(New-Object System.Speech.Synthesis.SpeechSynthesizer)."
            "GetInstalledVoices() | ForEach-Object { "
            "$_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name "
            "}"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=20, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "voices": [], "error": str(exc)}
        if result.returncode != 0:
            return {"ok": False, "voices": [], "error": result.stderr.strip()}
        voices = [
            tuple(line.split("|", 1))
            for line in result.stdout.splitlines()
            if "|" in line
        ]
        return {"ok": True, "voices": voices, "error": ""}


def _b64(text: str) -> str:
    """Base64 UTF-8 — the Unicode-safe channel through PowerShell argv."""
    import base64

    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class SpeechToolConnector:
    """Adapts :class:`SpeechTool` to the ``Connector`` protocol."""

    def __init__(self, tool: SpeechTool | None = None) -> None:
        self._tool = tool if tool is not None else SpeechTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "speak") or "speak"
        if operation == "speak":
            result = self._tool.speak(
                params.get("text", ""),
                out_wav=params.get("out_wav", ""),
            )
        elif operation == "voices":
            result = self._tool.list_voices()
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={k: v for k, v in result.items() if k != "error"})


__all__ = ["SpeechTool", "SpeechToolConnector"]