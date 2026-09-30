"""System status — the REAL machine's vitals in one honest report.

R53 wave-6: «وضعیت سیستم را بگو» used to fall to a goal/pdf route. Now one
capability reads the REAL Windows vitals: uptime (CIM LastBootUpTime), RAM
(total/free/used percent), disk roots (free/total per drive), and battery
(Win32_Battery). Every number is measured, never estimated; an unreadable
signal is NAMED, never invented. Persian-rendered by persian_report.
"""

from __future__ import annotations

import subprocess
from typing import Any

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _ps(script: str, timeout: int = 20) -> str:
    """Run a PowerShell probe; empty string on any failure (honest)."""
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        return (out.stdout or "").strip() if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _fa_num(v: int | float | str) -> str:
    return str(v).translate(_FA)


class SystemStatusTool:
    """Real Windows vitals — measured, honest, Persian-ready."""

    name = "sysstatus"
    capability = "system_status"

    def status(self) -> dict[str, Any]:
        """Gather uptime, RAM, disks, battery. Every field measured or named."""
        out: dict[str, Any] = {"ok": True, "error": ""}

        # UPTIME — CIM LastBootUpTime (ISO-forced; the locale lesson)
        raw = _ps("(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss')")
        if raw:
            try:
                from datetime import datetime

                boot = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - boot
                out["uptime"] = {
                    "days": delta.days,
                    "hours": delta.seconds // 3600,
                    "minutes": (delta.seconds % 3600) // 60,
                    "boot": raw,
                }
            except ValueError:
                out["uptime"] = None
        else:
            out["uptime"] = None  # honest absence, never a guess

        # RAM — Win32_OperatingSystem TotalVisibleMemorySize/FreePhysicalMemory (KB)
        raw = _ps(
            "$os = Get-CimInstance Win32_OperatingSystem; "
            "$os.TotalVisibleMemorySize.ToString() + '|' + $os.FreePhysicalMemory.ToString()"
        )
        if raw and "|" in raw:
            total_kb, free_kb = (int(x) for x in raw.split("|", 1))
            out["ram"] = {
                "total_gb": round(total_kb / (1024 * 1024), 1),
                "free_gb": round(free_kb / (1024 * 1024), 1),
                "used_pct": round(100 * (total_kb - free_kb) / total_kb, 1) if total_kb else 0,
            }
        else:
            out["ram"] = None

        # DISKS — every drive's free/total
        raw = _ps(
            "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object "
            "{ $_.DeviceID + '|' + $_.FreeSpace.ToString() + '|' + $_.Size.ToString() }"
        )
        disks = []
        if raw:
            for line in raw.splitlines():
                parts = line.strip().split("|")
                if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                    free_b, total_b = int(parts[1]), int(parts[2])
                    disks.append({
                        "drive": parts[0],
                        "free_gb": round(free_b / (1024 ** 3), 1),
                        "total_gb": round(total_b / (1024 ** 3), 1),
                        "free_pct": round(100 * free_b / total_b, 1) if total_b else 0,
                    })
        out["disks"] = disks if disks else None

        # BATTERY — EstimatedChargeRemaining (absent on desktops = None)
        raw = _ps(
            "(Get-CimInstance Win32_Battery).EstimatedChargeRemaining"
        )
        if raw and raw.replace(".", "").isdigit():
            out["battery_pct"] = int(float(raw))
        else:
            out["battery_pct"] = None

        # honest summary of what could NOT be read
        missing = [k for k in ("uptime", "ram", "disks") if out.get(k) in (None, [],)]
        if missing:
            out["notes"] = [f"سیگنال {k} خوانده نشد" for k in missing]
        else:
            out["notes"] = []
        return out


class SystemStatusToolConnector:
    """Adapts :class:`SystemStatusTool` to the ``Connector`` protocol."""

    def __init__(self, tool: SystemStatusTool | None = None) -> None:
        self._tool = tool if tool is not None else SystemStatusTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "status") or "status"
        if operation != "status":
            return ConnectorResult(ok=False, output=None, error=f"عملیات ناشناخته: {operation!r}")
        result = self._tool.status()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={k: v for k, v in result.items() if k != "error"})


__all__ = ["SystemStatusTool", "SystemStatusToolConnector", "_fa_num"]
