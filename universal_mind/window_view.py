"""THE WINDOW & PROCESS VIEW — what is open, what is heavy (R59 P3+P4).

Two measured dead sentences:
  «چه برنامه‌هایی الان باز است؟»   — the operator's OPEN WINDOWS
  «پروسه‌های پرمصرف را نشان بده»  — the machine's HEAVIEST processes

Both are read-only views of the REAL machine through PowerShell (the same
WMI/CIM path the uptime and system-status tools already use). Laws:
  - READ-ONLY: this module never terminates, starts, or changes a process.
  - An empty answer is honest («هیچ پنجره‌ای باز نیست»), never padded.
  - Every number rendered to the operator is Persian.
  - A PowerShell failure is returned BY NAME, never swallowed into empty.
"""

from __future__ import annotations

import subprocess
from typing import Any

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_PS_TIMEOUT = 15


def _run_ps(script: str) -> str:
    """Run a read-only PowerShell snippet; raise with the real error text.

    Output is read as UTF-8 (with `[Console]::OutputEncoding` set first):
    the default OEM codepage turns a Persian window title into `??????`,
    and a view that renders the operator's own tabs as question marks is a
    silent corruption, not a view.
    """
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script],
        capture_output=True, timeout=_PS_TIMEOUT,
    )
    if out.returncode != 0:
        err = out.stderr.decode("utf-8", errors="replace").strip()[:200]
        raise RuntimeError(err or f"exit {out.returncode}")
    return out.stdout.decode("utf-8", errors="replace") or ""


def _fa(value: object) -> str:
    return str(value).translate(_FA)


def list_open_windows() -> dict[str, Any]:
    """The operator's real open windows (process name + window title)."""
    try:
        raw = _run_ps(
            "Get-Process | Where-Object { $_.MainWindowTitle } | "
            "Select-Object ProcessName, MainWindowTitle | "
            "ConvertTo-Json -Compress"
        )
    except Exception as exc:  # noqa: BLE001 — surfaced by name, never swallowed
        return {"ok": False, "error": f"خواندن پنجره‌ها نشد: {exc}", "windows": []}
    import json

    try:
        data = json.loads(raw) if raw.strip() else []
    except ValueError:
        return {"ok": False, "error": "پاسخ PowerShell شکل شناخته نداشت", "windows": []}
    if isinstance(data, dict):
        data = [data]
    windows = [
        {"process": str(w.get("ProcessName", "")), "title": str(w.get("MainWindowTitle", ""))}
        for w in data
        if w.get("MainWindowTitle")
    ]
    return {"ok": True, "windows": windows, "error": ""}


def top_processes(limit: int = 5) -> dict[str, Any]:
    """The machine's heaviest processes by CPU (real WorkingSet too)."""
    n = max(1, min(int(limit), 20))
    try:
        raw = _run_ps(
            "Get-Process | Sort-Object CPU -Descending | "
            f"Select-Object -First {n} ProcessName, CPU, WorkingSet64 | "
            "ConvertTo-Json -Compress"
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"خواندن پردازش‌ها نشد: {exc}", "processes": []}
    import json

    try:
        data = json.loads(raw) if raw.strip() else []
    except ValueError:
        return {"ok": False, "error": "پاسخ PowerShell شکل شناخته نداشت", "processes": []}
    if isinstance(data, dict):
        data = [data]
    procs = [
        {
            "process": str(p.get("ProcessName", "")),
            "cpu_seconds": float(p.get("CPU") or 0.0),
            "ram_mb": round(float(p.get("WorkingSet64") or 0) / (1024 * 1024), 1),
        }
        for p in data
    ]
    # sort in PYTHON too, not only in PowerShell: the view's contract is
    # "heaviest first", and trusting the wire's ordering makes the contract
    # a hope. A stable sort keeps equal-CPU processes in their given order.
    procs.sort(key=lambda p: p["cpu_seconds"], reverse=True)
    return {"ok": True, "processes": procs, "error": ""}


def windows_fa(result: dict[str, Any]) -> str:
    """The Persian answer for the open-windows view."""
    if not result.get("ok"):
        return str(result.get("error"))
    ws = result.get("windows") or []
    if not ws:
        return "هیچ پنجره‌ای باز نیست."
    lines = [f"{_fa(len(ws))} پنجره باز است:"]
    for w in ws[:15]:
        lines.append(f"  • {w['process']}" + (f" — {w['title'][:50]}" if w["title"] else ""))
    if len(ws) > 15:
        lines.append(f"  … و {_fa(len(ws) - 15)} مورد دیگر")
    return "\n".join(lines)


def processes_fa(result: dict[str, Any]) -> str:
    """The Persian answer for the heavy-processes view."""
    if not result.get("ok"):
        return str(result.get("error"))
    ps = result.get("processes") or []
    if not ps:
        return "پردازشی برای نمایش پیدا نشد."
    lines = [f"{_fa(len(ps))} پردازشِ پرمصرف (مرتب بر CPU):"]
    for i, p in enumerate(ps, start=1):
        lines.append(
            f"  {_fa(i)}. {p['process']} — CPU: {_fa(round(p['cpu_seconds']))} ثانیه، "
            f"رم: {_fa(p['ram_mb'])} مگابایت"
        )
    return "\n".join(lines)


__all__ = ["list_open_windows", "processes_fa", "top_processes", "windows_fa"]
