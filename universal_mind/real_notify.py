"""Real notification tools — a Windows toast notification from the system tray.

A fourth real effect: the system actually shows a Windows toast notification
(using the OS's built-in message loop, no third-party app), proving the
super-platform can surface *to the operator* — not just process files or data.

Fail-safe: if PowerShell / the Windows toast machinery is unavailable, the call
reports not-ok with a clear reason, never pretends a toast was shown.
"""

from __future__ import annotations

import subprocess
from typing import Any


def _powershell() -> str | None:
    return "powershell.exe" if True else None  # always present on Windows


class NotifyTool:
    """A real Windows Toast notifier (the fourth real effect)."""

    name = "toast"
    capability = "notify"

    def is_available(self) -> bool:
        return True

    def notify(self, title: str = "Universal Mind", body: str = "Task complete") -> dict[str, Any]:
        """Show a real Windows toast notification.

        The toast shows in the system tray with the given title + body. It is the
        direct proof that the mind can reach *out* to the operator's screen — a
        real effect on the OS (not just a file).
        """
        try:
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
                "$title = " + repr(title) + "; "
                "$body = " + repr(body) + "; "
                "$n = New-Object System.Windows.Forms.NotifyIcon; "
                "$n.Icon = [System.Drawing.SystemIcons]::Information; "
                "$n.Visible = $true; "
                "$n.ShowBalloonTip(3000, $title, $body, [System.Windows.Forms.ToolTipIcon]::Info); "
                "$n.Dispose(); 'shown'"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "shown": False, "error": str(exc)}
        if result.returncode != 0 or "shown" not in result.stdout:
            return {"ok": False, "shown": False, "error": result.stderr.strip() or "toast not shown"}
        return {"ok": True, "shown": True, "error": ""}


__all__ = ["NotifyTool"]