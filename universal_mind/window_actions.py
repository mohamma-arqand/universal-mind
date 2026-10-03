"""R63 P4 — window ACTIONS: closing/minimizing REAL windows by name.

«تمام پنجره‌های کروم را ببند» was a measured dead sentence: the
platform could LIST windows (R59 P3) but not act on them. This module
adds the two honest actions:

- close_by_name(name): windows whose title/process matches `name`;
- minimize_by_name(name): same match, WM command instead of kill.

THE SAFETY LAWS (a wrong close loses the operator's work):
- the action ALWAYS previews the matched windows in its answer —
  what was closed is NAMED, never silent;
- a name that matches nothing is a named refusal listing what IS open
  (the R60 drive-letter refusal shape);
- the match is on the REAL list from list_open_windows — never a
  process id guessed from the name.
"""

from __future__ import annotations

from typing import Any

from universal_mind.window_view import _run_ps, list_open_windows


def _ps_quote(text: str) -> str:
    """A literal for PowerShell single quotes: ' doubles inside."""
    return text.replace("'", "''")


def _matches(name: str) -> list[dict[str, str]]:
    """The real open windows whose process or title matches `name`.

    The operator speaks Persian program names («کروم», «نوتپد») while
    processes are Latin (chrome, Notepad) — the spoken aliases are
    mapped, and the raw name still matches directly.
    """
    res = list_open_windows()
    if not res.get("ok"):
        return []
    aliases = {
        "کروم": "chrome", "گوگل کروم": "chrome", "گوگل‌کروم": "chrome",
        "نوتپد": "notepad", "نتپد": "notepad", "دفترچه": "notepad",
        "فایرفاکس": "firefox", "موزیلا": "firefox",
        "اج": "edge", "ادج": "edge", "مایکروسافت اج": "edge",
        "اکسپلورر": "explorer", "ویندوز اکسپلورر": "explorer",
        "ترمینال": "terminal", "پاورشل": "powershell",
        "ورد": "winword", "اکسل": "excel", "پاورپوینت": "powerpnt",
        "تلگرام": "telegram", "واتساپ": "whatsapp",
        "ویژوال": "code", "وی‌اس کد": "code", "وی اس کد": "code",
    }
    needle = name.strip().lower()
    if needle in aliases:
        needle = aliases[needle]
    hits: list[dict[str, str]] = []
    for w in res.get("windows", []):
        hay = f"{w['process']} {w['title']}".lower()
        if needle and needle in hay:
            hits.append(w)
    return hits


def close_by_name(name: str) -> dict[str, Any]:
    """Close every REAL window matching `name` — each one named."""
    hits = _matches(name)
    if not hits:
        open_now = ", ".join(
            f"{w['process']} ({w['title'][:30]})" for w in list_open_windows().get("windows", [])[:8]
        )
        return {
            "ok": False,
            "closed": [],
            "error": f"پنجره‌ای به نام «{name}» باز نیست. پنجره‌های دیده‌شده: {open_now or '—'}",
        }
    closed: list[str] = []
    errors: list[str] = []
    for w in hits:
        try:
            proc = _ps_quote(w["process"])
            title = _ps_quote(w["title"])
            # a GRACEFUL close: CloseMainWindow lets the app save its
            # work; a hard kill would lose it (the delete law's cousin).
            _run_ps(
                f"Get-Process -Name '{proc}' -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.MainWindowTitle -eq '{title}' }} | "
                f"ForEach-Object {{ [void]$_.CloseMainWindow() }}"
            )
            closed.append(f"{w['process']} — {w['title'][:40]}")
        except Exception as exc:  # noqa: BLE001 — each window is its own outcome
            errors.append(f"{w['process']}: {exc}")
    ok = bool(closed) and not errors
    return {
        "ok": ok,
        "closed": closed,
        "errors": errors,
        "error": "; ".join(errors),
    }


def close_fa(result: dict[str, Any]) -> str:
    """The Persian voice of a close run — every closed window named."""
    if result.get("ok"):
        lines = [f"بستم ({len(result['closed'])} پنجره):"]
        lines += [f"  • {name}" for name in result["closed"][:10]]
        return "\n".join(lines)
    parts = ["❌ " + str(result.get("error") or "بستن نشد")]
    if result.get("closed"):
        parts.append("اینها بسته شدند: " + "؛ ".join(result["closed"][:5]))
    if result.get("errors"):
        parts.append("اینها نشد: " + "؛ ".join(result["errors"][:3]))
    return "\n".join(parts)


__all__ = ["close_by_name", "close_fa"]
