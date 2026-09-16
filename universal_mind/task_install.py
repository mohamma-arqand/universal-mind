"""Install the proactive tick into Windows Task Scheduler — one command.

`universal-mind install-tick` registers a REAL Windows scheduled task that
runs the platform's tick every hour (the platform wakes ITSELF up). The
installation is honest and reversible:

- the exact schtasks command and the task name are printed;
- `--uninstall` removes the task by name;
- the tick task runs whether or not the operator is logged in interactively
  is NOT claimed (schtasks defaults are kept — what Windows really accepts
  is what gets installed, and the result is read back).

No elevation is claimed: a per-user task installs without admin on modern
Windows; if schtasks reports a failure (e.g. the binary path is not what
Windows wants), the exact error is returned — never a fabricated success.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

TASK_NAME = "UniversalMind-ProactiveTick"


def _tick_command() -> str:
    """The absolute python + tick invocation, quoted for schtasks /TR."""
    python = os.path.abspath(sys.executable)
    here = os.path.dirname(os.path.abspath(__file__))
    tick = os.path.abspath(os.path.join(here, "scripts", "scheduler_tick.py"))
    return f'"{python}" "{tick}"'


def install(*, hourly: int = 1) -> dict[str, Any]:
    """Register the hourly tick task (a real schtasks call, read back)."""
    # /SC HOURLY /MO n → every n hours; per-user task, no /RU (no admin claim).
    cmd = [
        "schtasks.exe", "/Create", "/TN", TASK_NAME,
        "/TR", _tick_command(),
        "/SC", "HOURLY", "/MO", str(max(1, hourly)),
        "/F",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "error": str(exc), "task": TASK_NAME}
    if result.returncode != 0:
        return {
            "ok": False,
            "error": (result.stderr.strip() or result.stdout.strip() or "schtasks failed"),
            "task": TASK_NAME,
        }
    # READ IT BACK — a claimed install that cannot be found is not installed.
    verify = _query()
    return {
        "ok": verify["ok"],
        "task": TASK_NAME,
        "command": _tick_command(),
        "readback": verify.get("detail", ""),
        "error": "" if verify["ok"] else verify.get("error", "installed but not found"),
    }


def uninstall() -> dict[str, Any]:
    """Remove the tick task by name (idempotent: missing task is success)."""
    cmd = ["schtasks.exe", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "error": str(exc), "task": TASK_NAME}
    if result.returncode != 0 and "cannot find" not in result.stderr.lower():
        return {"ok": False, "error": result.stderr.strip(), "task": TASK_NAME}
    return {"ok": True, "task": TASK_NAME, "error": ""}


def _query() -> dict[str, Any]:
    """The real Task Scheduler read-back for our task."""
    cmd = ["schtasks.exe", "/Query", "/TN", TASK_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    detail = result.stdout.strip()
    return {
        "ok": result.returncode == 0,
        "detail": detail[:400],
        "error": result.stderr.strip() if result.returncode != 0 else "",
    }


__all__ = ["TASK_NAME", "install", "uninstall"]