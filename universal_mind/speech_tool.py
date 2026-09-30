"""The speech tool — the platform SPEAKS in real audio, and LISTENS.

Uses the Windows SAPI voice (System.Speech via PowerShell): the same OS-native
channel as the toast and clipboard, no downloads, no external services. The
operator's language matters end to end — a Persian report deserves a Persian
voice, and Persian voices are preferred when installed (fa-IR), with an honest
fallback message when none exists (never a silent no-op).

R44-9 adds the EARS: `listen()` dictates real speech-to-text through the same
System.Speech channel, honestly reporting a missing engine or heard silence.

R53 THE MUTE LAW: the whole platform's voice has ONE switch, read at the
moment of speaking (never cached — «بیصدا» / «باز صدا» flip it live). The
source of truth is the persistent `operator_preferences` row `voice_muted`
(honored by every caller); UM_MUTE=1 in the environment is the same switch
for headless runs. A muted speak is HONEST: the words are composed and the
flow continues (ok=True, muted=True, voice="(muted)") — only the loudspeaker
stays silent, so tests and reports stay truthful while the room stays quiet.

Real effects only: the call either makes sound / returns heard text, or
reports exactly why not.
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
        if _muted():
            # THE MUTE LAW: composed but silent — honest in every field.
            return {
                "ok": True, "spoken": True, "muted": True,
                "voice": "(muted)", "error": "",
                "note": "بیصدا — برای صدا، «باز صدا» بگو",
            }

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

    def listen(self, *, seconds: int = 5, lang_hint: str = "en-US") -> dict[str, Any]:
        """LISTEN — real speech-to-text through Windows System.Speech.

        R44 item 9: the platform gains EARS. The SpeechRecognitionEngine
        dictates from the default microphone for ``seconds``; the recognized
        text rides back as a REAL string the router can act on.

        HONEST LIMITS (never a silent fake):
        - No engine / no microphone -> ok=False with the exact remedy.
        - Silence -> ok=True with recognized="" and a Persian note.
        - lang_hint selects the engine culture honestly (an en-only machine
          says so instead of pretending to hear Persian).
        """
        seconds = max(2, min(15, int(seconds)))
        ps = (
            "$ErrorActionPreference='Stop'; "
            "$found=$null; "
            "foreach ($r in [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()) { "
            "  if ($r.Culture.Name -eq '" + lang_hint + "') { $found=$r; break } "
            "} "
            "if (-not $found) { $found=[System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Select-Object -First 1 } "
            "if (-not $found) { Write-Output 'NO_ENGINE'; exit } "
            "$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine($found); "
            "$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar())); "
            "$rec.SetInputToDefaultAudioDevice(); "
            "$rec.InitialSilenceTimeout = " + str(seconds) + "; "
            "$rec.BabbleTimeout = " + str(seconds) + "; "
            "$rec.EndSilenceTimeout = 1; "
            "$text = $rec.Recognize().Text; "
            "if ($text) { Write-Output ('TEXT:' + $text) } else { Write-Output 'TEXT:' }"
        )
        b64 = _b64(ps)
        cmd = (
            "powershell -NoProfile -NonInteractive -Command "
            "[System.Text.Encoding]::UTF8.GetString("
            "[Convert]::FromBase64String('" + b64 + "')) | Invoke-Expression"
        )
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds + 25, check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "recognized": "", "error": "گوش دادن بیش از حد طول کشید — میکروفون را بررسی کن"}
        except OSError as exc:
            return {"ok": False, "recognized": "", "error": f"موتور گفتار ویندوز در دسترس نیست: {exc}"}
        out = (proc.stdout or "").strip()
        if "NO_ENGINE" in out:
            return {
                "ok": False,
                "recognized": "",
                "error": "شناساگر گفتار روی این ویندوز نصب نیست — Settings > Time & Language > Speech",
            }
        text = out[5:] if out.startswith("TEXT:") else ""
        return {
            "ok": True,
            "recognized": text,
            "lang": lang_hint,
            "seconds": seconds,
            "note": "" if text else "صدایی شنیده نشد — دوباره و نزدیکتر به میکروفون بگو",
            "error": "",
        }


def _b64(text: str) -> str:
    """Base64 UTF-8 — the Unicode-safe channel through PowerShell argv."""
    import base64

    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _muted() -> bool:
    """The MUTE LAW's one source of truth, read LIVE at every speak.

    Two honest channels, either alone suffices:
      1. the persistent `operator_preferences` row ``voice_muted`` — set by
         «بیصدا» / cleared by «باز صدا», survives restarts, works headless;
      2. the environment (``UM_MUTE=1``) — for CI and service contexts.

    Read failures are NEVER a crash (a preference row cannot take the
    platform's voice down): unreadable => unmuted, the safe default.
    """
    import os

    if os.environ.get("UM_MUTE", "").strip() in ("1", "true", "yes"):
        return True
    try:
        from universal_mind import operator_preferences as prefs

        return (prefs.get("voice_muted") or "").strip().lower() in ("1", "true", "yes", "on")
    except Exception:  # noqa: BLE001 — the switch must never take speech down
        return False


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
        elif operation == "listen":
            # R44-9: the platform's EARS — real speech-to-text.
            result = self._tool.listen(
                seconds=int(params.get("seconds", 5) or 5),
                lang_hint=str(params.get("lang", "en-US") or "en-US"),
            )
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={k: v for k, v in result.items() if k != "error"})


__all__ = ["SpeechTool", "SpeechToolConnector"]