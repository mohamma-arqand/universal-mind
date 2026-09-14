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


class ClipboardTool:
    """A real clipboard specialist (read from / write to the OS clipboard)."""

    name = "clipboard"
    capability = "clipboard"

    def set_text(self, text: str) -> dict[str, Any]:
        if not text:
            return {"ok": False, "outcome": "", "error": "empty text"}
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", f"Set-Clipboard -Value {text!r}"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "outcome": "", "error": str(exc)}
        if result.returncode != 0:
            return {"ok": False, "outcome": "", "error": result.stderr.strip() or "set-clipboard failed"}
        return {"ok": True, "outcome": text, "error": ""}

    def get_text(self) -> dict[str, Any]:
        """Return the real text currently on the clipboard (or an error)."""
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "outcome": "", "error": str(exc)}
        if result.returncode != 0:
            return {"ok": False, "outcome": "", "error": result.stderr.strip() or "get-clipboard failed"}
        text = result.stdout.rstrip("\r\n")
        if not text.strip():
            return {"ok": False, "outcome": "", "error": "clipboard is empty"}
        return {"ok": True, "outcome": text, "error": ""}


__all__ = ["ClipboardTool"]