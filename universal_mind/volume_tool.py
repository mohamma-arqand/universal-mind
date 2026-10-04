"""R79 A1 — the REAL Windows volume control (via the compiled volctl.exe).

«صدا را بلندتر کن» claimed success while the real system volume never
moved — a false success, the worst kind of lie. This tool drives the
compiled WASAPI helper (tools/volctl.exe, built from tools_src/volctl.cs
with the framework csc.exe — no PyPI, no downloads) and reports the
MEASURED before:after. A muted endpoint is UNMUTED first (a volume
change under mute is silent nothing) and that fact is NAMED.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

_EXE = Path(__file__).resolve().parent / "tools" / "volctl.exe"


def _run(args: list[str]) -> dict[str, Any]:
    if not _EXE.exists():
        return {"ok": False,
                "error": "ابزار ولوم (tools/volctl.exe) ساخته نشده — با csc.exe بساز"}
    try:
        r = subprocess.run([str(_EXE), *args], capture_output=True, text=True,
                           timeout=20, check=False)
    except OSError as exc:
        return {"ok": False, "error": f"اجرای ابزار ولوم نشد: {exc}"}
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return {"ok": False, "error": f"ولوم دستور نشد: {(r.stderr or out)[:80]}"}
    return {"ok": True, "out": out, "error": ""}


def get_volume() -> dict[str, Any]:
    """The MEASURED master volume (0-100) and mute state."""
    r = _run(["get"])
    if not r["ok"]:
        return r
    try:
        vol_s, mute_s = r["out"].split(":")
        return {"ok": True, "volume": int(vol_s), "muted": mute_s == "1", "error": ""}
    except ValueError:
        return {"ok": False, "error": f"پاسخ ناخوانا: {r['out'][:40]}"}


def set_volume(*, delta: float | None = None, level: float | None = None) -> dict[str, Any]:
    """Move the REAL master volume: delta (±0..1) or absolute level (0..1).

    Returns the MEASURED before:after and whether a mute was lifted.
    Nothing happening (already at the ceiling/floor) is honest too."""
    if delta is None and level is None:
        return {"ok": False, "error": "نه مقدار دادی نه درصد — «بلندتر/آرومتر/روی ۵۰»"}
    if level is not None:
        r = _run(["set", str(int(max(0.0, min(100.0, round(level * 100)))))])
    elif (delta or 0) > 0:
        r = _run(["up"])
    elif (delta or 0) < 0:
        r = _run(["down"])
    else:
        return get_volume()
    if not r["ok"]:
        return r
    try:
        before_s, after_s, unmute_s = r["out"].split(":")
        before, after = int(before_s), int(after_s)
    except ValueError:
        return {"ok": False, "error": f"پاسخ ناخوانا: {r['out'][:40]}"}
    return {"ok": True, "before": before, "after": after, "changed": after != before,
            "unmuted": unmute_s == "1", "error": ""}


__all__ = ["get_volume", "set_volume"]
