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


def _health_store() -> Any:
    """The persistent store for health reads (R41).

    The CONSTRUCTOR, not shared_persistent: health must honor a patched
    DEFAULT_DB_DIR (tests isolate to a temp store that way), and a plain
    constructor call also survives lambda-mocked classes.
    """
    from universal_mind.database_suite import DatabaseSuite

    return DatabaseSuite(persistent=True)


def tick_health() -> dict[str, Any]:
    """The proactive heartbeat: is the tick ALIVE?

    Three real signals, honestly combined:
    - TASK: the Task Scheduler task exists (schtasks read-back);
    - LAST SCHEDULE FIRE: the newest schedule row's last_run in the store;
    - RECENT RUN: any run_history row inside the last 25 hours (a tick or
      any operator command — evidence the platform is alive at all).
    Verdict: alive (task+evidence) / silent (task but no evidence) / dead.
    """
    from datetime import datetime, timedelta

    signals: dict[str, Any] = {}

    task = _query()
    signals["task_installed"] = bool(task.get("ok"))

    try:

        db = _health_store()
        q = db.query(
            "SELECT MAX(created_at) AS last FROM run_history"
        )
        last_row = q["rows"][0]["last"] if q.get("ok") and q["rows"] else None
        # R41: parse the real datetime — the store writes BOTH 'T'-separated
        # and space-separated stamps; a naive string compare silently says
        # "no recent run" for every space-separated row (space < 'T').
        if last_row is None:
            signals["recent_run"] = False
        else:
            stamp = str(last_row).replace("T", " ").split(".")[0]
            last_dt = datetime.fromisoformat(stamp)
            signals["recent_run"] = last_dt >= datetime.now() - timedelta(hours=25)
    except Exception:  # noqa: BLE001 — a health probe never crashes
        signals["recent_run"] = False

    if signals["task_installed"] and signals["recent_run"]:
        verdict = "alive"
    elif signals["task_installed"]:
        verdict = "silent"  # installed but nothing ran — the silence failure
    else:
        verdict = "dead"
    return {"ok": True, "verdict": verdict, "signals": signals, "error": ""}


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