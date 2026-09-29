"""Real clipboard tools — read / write the actual system clipboard.

A fourth real effect: the platform can push text onto the system clipboard or read
what is already there, so a run can *hand* text to (or take text from) any other
app the operator is using. Uses PowerShell on Windows (no extra package), so it is
deterministic and local.

Fail-safe: an empty / unavailable clipboard read returns not-ok with a clear reason,
never a fabricated string.
"""

from __future__ import annotations

import subprocess
from typing import Any


def _named_clip_error(stderr: str, verb: str) -> str:
    """Name a clipboard refusal honestly — the Windows clipboard is a GLOBAL
    OS resource: another app can hold it (CLIPBRD_E_CANT_OPEN), and that is a
    named, actionable state, never a bare English traceback in the operator's
    Persian report."""
    tail = (stderr or "").strip()
    if "ExternalException" in tail or "CANT_OPEN" in tail:
        return (f"کلیپبورد قفل شده — {verb} الان ممکن نیست؛ "
                "یک برنامهی دیگر کلیپبورد را در اختیار دارد. دوباره تلاش کن.")
    return tail or "کلیپبورد در دسترس نیست"


class ClipboardTool:
    """A real clipboard specialist (read from / write to the OS clipboard)."""

    name = "clipboard"
    capability = "clipboard"

    def set_text(self, text: str) -> dict[str, Any]:
        if not text:
            return {"ok": False, "outcome": "", "error": "empty text"}
        # PowerShell argv mangles non-ASCII (Persian becomes '????'), so the
        # text travels as a Base64 UTF-16LE payload — the canonical way to pass
        # arbitrary Unicode into a -Command without an encoding layer in between.
        import base64

        b64 = base64.b64encode(text.encode("utf-16-le")).decode("ascii")
        try:
            # decode inside PowerShell: stdin carries the Base64 (ASCII-safe),
            # the decoded UTF-16LE text goes to the clipboard losslessly.
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 f"$b = [Convert]::FromBase64String('{b64}'); "
                 f"$t = [System.Text.Encoding]::Unicode.GetString($b); "
                 "Set-Clipboard -Value $t"],
                capture_output=True, text=True, timeout=15, check=False,
                input="",
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "outcome": "", "error": str(exc)}
        if result.returncode != 0:
            return {"ok": False, "outcome": "",
                    "error": _named_clip_error(result.stderr, "نوشتن")}
        return {"ok": True, "outcome": text, "error": ""}

    def get_text(self) -> dict[str, Any]:
        """Return the real text currently on the clipboard (or an error)."""
        import base64

        # Reading must survive the same encoding wall as writing: the clipboard
        # text comes back as Base64 UTF-16LE (round-trips any Unicode), then is
        # decoded here — Get-Clipboard's raw stdout would mangle Persian.
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "$t = Get-Clipboard; [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($t))"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "outcome": "", "error": str(exc)}
        if result.returncode != 0:
            return {"ok": False, "outcome": "",
                    "error": _named_clip_error(result.stderr, "خواندن")}
        b64 = result.stdout.strip()
        if not b64:
            return {"ok": False, "outcome": "", "error": "clipboard is empty"}
        try:
            text = base64.b64decode(b64).decode("utf-16-le")
        except (ValueError, UnicodeDecodeError) as exc:
            return {"ok": False, "outcome": "", "error": f"clipboard decode failed: {exc}"}
        if not text.strip():
            return {"ok": False, "outcome": "", "error": "clipboard is empty"}
        return {"ok": True, "outcome": text, "error": ""}


__all__ = ["ClipboardTool"]