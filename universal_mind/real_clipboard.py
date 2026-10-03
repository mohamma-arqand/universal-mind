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


def _clipboard_holder() -> str:
    """WHO holds the clipboard right now — the honest answer names the real
    holder (window title + process name), never a vague «برنامهی دیگر».
    R75: on this machine cua-driver (a Computer-Use overlay) holds the
    clipboard permanently; naming it turned an unsolvable riddle into an
    actionable fact."""
    try:
        import subprocess as _sp

        r = _sp.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Add-Type -MemberDefinition '[DllImport(\"user32.dll\")] public"
             " static extern IntPtr GetOpenClipboardWindow(); [DllImport("
             "\"user32.dll\")] public static extern uint GetWindowThreadProcessId("
             "IntPtr h, out uint pid);' -Name U -Namespace W;"
             "$h = [W.U]::GetOpenClipboardWindow();"
             "if ($h -ne [IntPtr]::Zero) {"
             "  $pid2 = 0; [W.U]::GetWindowThreadProcessId($h, [ref]$pid2) | Out-Null;"
             "  $p = Get-Process -Id $pid2 -ErrorAction SilentlyContinue;"
             "  if ($p) { Write-Output ($p.Name + ':' + $p.Id) } }"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        holder = (r.stdout or "").strip()
        if holder and ":" in holder:
            name, pid = holder.rsplit(":", 1)
            if name:
                return f"برنامهٔ «{name}» (شناسهٔ {pid})"
    except Exception:  # noqa: BLE001 — the holder is a VIEW, never fatal
        pass
    # R75 — a UIA-layer holder (cua-driver: the Computer-Use overlay) never
    # appears in GetOpenClipboardWindow (it holds via the UIAutomation path),
    # but the PROCESS is visible. Known clipboard-guard processes are named
    # if running; each was measured to hold the clipboard on a real machine.
    try:
        import subprocess as _sp2

        r2 = _sp2.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "$guards = 'cua-driver','cua-driver-uia','cua-cursor-theme',"
             "'msteams','discord','ClipClip','Ditto','1Clipboard','CopyQ';"
             "$found = Get-Process -Name $guards -ErrorAction SilentlyContinue"
             " | Select-Object -First 1;"
             "if ($found) { Write-Output ($found.Name + ':' + $found.Id) }"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        g = (r2.stdout or "").strip()
        if g and ":" in g:
            name, pid = g.rsplit(":", 1)
            return f"برنامهٔ «{name}» (شناسهٔ {pid})"
    except Exception:  # noqa: BLE001
        pass
    return ""


def _named_clip_error(stderr: str, verb: str) -> str:
    """Name a clipboard refusal honestly — the Windows clipboard is a GLOBAL
    OS resource: another app can hold it (CLIPBRD_E_CANT_OPEN), and that is a
    named, actionable state, never a bare English traceback in the operator's
    Persian report. R75: the holder is NAMED when the OS lets us see it."""
    tail = (stderr or "").strip()
    if "ExternalException" in tail or "CANT_OPEN" in tail:
        holder = _clipboard_holder()
        who = f" — {holder} آن را در اختیار دارد" if holder else (
            " — یک برنامهی دیگر آن را در اختیار دارد"
        )
        return (f"کلیپبورد قفل شده — {verb} الان ممکن نیست{who}. "
                "برنامهٔ دارنده را ببند یا دوباره تلاش کن.")
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
        # R75 P4 — TRANSIENT LOCKS DESERVE RETRIES: a clipboard holder that
        # keeps the resource for milliseconds (drag operations, overlays)
        # should not fail a write forever; three attempts with a growing
        # delay. A PERMANENT holder (cua-driver) still fails — named.
        import time as _time

        result = None
        last_err = ""
        for _attempt in range(3):
            try:
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
            if result.returncode == 0:
                return {"ok": True, "outcome": text, "error": ""}
            last_err = result.stderr or ""
            _time.sleep(0.4 * (_attempt + 1))  # growing backoff
        return {"ok": False, "outcome": "",
                "error": _named_clip_error(last_err, "نوشتن")}
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