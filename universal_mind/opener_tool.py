"""R77 — the OPENER: «X را باز کن» opens the REAL thing on Windows.

«باز کن» used to fall to webfetch (a word collision): files, folders,
programs, settings, and even the calculator all asked «کدام سایت؟».
The opener runs the real Windows verb — ShellExecute — for each object
class, and names what it opened; an unknown object is a named refusal.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

# Persian program names -> the real executable (resolved at run time).
_PROGRAMS_FA: dict[str, str] = {
    "ماشینحساب": "calc",
    "ماشین حساب": "calc",
    "دفترچه یادداشت": "notepad",
    "نوشتار": "notepad",
    "paint": "mspaint",
    "نقاشی": "mspaint",
    "فایل اکسپلورر": "explorer",
    "فایل اکسپلورر را": "explorer",
    "اکسپلورر": "explorer",
    "تنظیمات ویندوز": "ms-settings:",
    "تنظیمات": "ms-settings:",
    "cmd": "cmd",
    "خط فرمان": "cmd",
    "پاورشل": "powershell",
    "task manager": "taskmgr",
    "مدیریت وظایف": "taskmgr",
    "مدیر وظایف": "taskmgr",
}


def open_target(target: str, *, verb: str = "") -> dict[str, Any]:
    """Open a REAL target on Windows: a path (file/folder), a program name,
    or a URL. Returns ok/kind/named; failures are named, never silent."""
    t = (target or "").strip().strip("'\u00ab\u00bb")
    if not t:
        return {"ok": False, "error": "چه چیزی را باز کنم؟ مسیر فایل، نام برنامه یا آدرس سایت را بگو."}

    # a URL opens in the DEFAULT browser
    if t.lower().startswith(("http://", "https://", "www.")) or (
        "." in t and " " not in t and "/" not in t and not Path(t).exists()
        and any(t.lower().endswith(s) for s in (".com", ".ir", ".org", ".net", ".io", ".dev"))
    ):
        if not t.lower().startswith(("http://", "https://")):
            t = "https://" + t
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                           f"Start-Process '{t}'"], capture_output=True,
                          text=True, timeout=20, check=False)
        if r.returncode != 0:
            return {"ok": False, "error": f"بازکردن «{t}» در مرورگر نشد: {r.stderr.strip()[:120]}"}
        return {"ok": True, "kind": "url", "opened": t, "error": ""}

    # a REAL path: file or folder (ShellExecute with the default verb,
    # or the named verb «با X» asks Windows to use that program)
    p = Path(t)
    if p.exists():
        if verb and p.is_file():
            r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Start-Process -FilePath '{verb}' -ArgumentList '{p}'"],
                               capture_output=True, text=True, timeout=20, check=False)
        else:
            r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Start-Process -FilePath '{p}'"],
                               capture_output=True, text=True, timeout=20, check=False)
        if r.returncode != 0:
            return {"ok": False,
                    "error": f"بازکردن «{t}» نشد: {r.stderr.strip()[:120]}"}
        kind = "پوشه" if p.is_dir() else "فایل"
        return {"ok": True, "kind": kind, "opened": str(p), "error": ""}

    # a Persian/Latin program name
    low = t.lower()
    prog = _PROGRAMS_FA.get(t) or _PROGRAMS_FA.get(low)
    if prog is None:
        for fa_name, exe in _PROGRAMS_FA.items():
            if fa_name in low:
                prog = exe
                break
    if prog:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            f"Start-Process '{prog}'"], capture_output=True,
                          text=True, timeout=20, check=False)
        if r.returncode != 0:
            return {"ok": False,
                    "error": f"بازکردن «{t}» نشد: {r.stderr.strip()[:120]}"}
        return {"ok": True, "kind": "برنامه", "opened": prog, "error": ""}

    return {"ok": False,
            "error": f"«{t}» نه مسیر موجود است، نه برنامهٔ شناختهشده — "
                     "مسیر دقیق یا نام برنامه را بگو (مثل: ماشینحساب، دفترچه یادداشت)."}


class OpenerConnector:
    """«X را باز کن» — the connector protocol for the registry."""

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        p = dict(params or {})
        target = str(p.get("target", "")).strip()
        verb = str(p.get("verb", "")).strip()
        if not target:
            return ConnectorResult(
                ok=False, output=None,
                error="چه چیزی را باز کنم؟ مسیر، نام برنامه یا آدرس را بگو.")
        from universal_mind.opener_tool import open_target

        res = open_target(target, verb=verb)
        if not res.get("ok"):
            return ConnectorResult(ok=False, output=None, error=str(res["error"]))
        return ConnectorResult(ok=True, output=res)

    def run(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        out = self.connect(None, dict(params or {}))
        return {"ok": out.ok, **(out.output or {}), "error": out.error or ""}

    def ops(self) -> dict[str, list[str]]:
        return {"open": ["file", "folder", "program", "url"]}
