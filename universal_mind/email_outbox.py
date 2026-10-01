"""The email outbox — a REAL message leaves the platform, honestly.

R44 item 11: «این گزارش را برایم ایمیل کن» produces a real RFC-822 .eml file
in the platform's outbox (always — offline, no account needed), and sends it
through SMTP when the operator has provided credentials IN THE ENVIRONMENT
(never in the repo, never in a document, never in a log line).

STANDARDS:
- The .eml is the deliverable: a real message file anyone can open, with the
  body, the attachment, the Subject — verifiable bytes on disk.
- SMTP is OPTIONAL and opt-in: without env credentials the tool says plainly
  «فایل ساخته شد، ارسال نشد — اعتبارنامهها تنظیم نشدهاند», never a fake send.
- A failed SMTP send still leaves the .eml (the work is never lost) and
  reports the REAL error.
- Credentials are read from env only and are NEVER echoed.
"""

from __future__ import annotations

import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any

# env names (values never appear in code, logs, or reports)
_ENV_HOST = "UM_SMTP_HOST"
_ENV_PORT = "UM_SMTP_PORT"
_ENV_USER = "UM_SMTP_USER"
_ENV_PASS = "UM_SMTP_PASS"


def _outbox_dir(out_dir: str | None = None) -> Path:
    target = Path(out_dir) if out_dir else Path(
        os.environ.get("UM_OUTBOX_DIR") or (Path.home() / "universal-mind-outbox")
    )
    target.mkdir(parents=True, exist_ok=True)
    return target


def compose(
    *,
    to: str = "",
    subject: str = "گزارش ذهن یکپارچه",
    body: str = "",
    attachment: str = "",
    out_dir: str | None = None,
) -> dict[str, Any]:
    """Compose a REAL .eml message file (and attach a real file when given)."""
    if not to:
        return {"ok": False, "error": "گیرنده مشخص نیست — «به آدرس ... ایمیل کن»", "path": ""}
    msg = EmailMessage()
    msg["From"] = os.environ.get("UM_SMTP_USER") or "universal-mind@localhost"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or "(بدون متن)")

    attached_bytes = 0
    if attachment:
        src = Path(attachment)
        if not src.exists():
            return {"ok": False, "error": f"پیوست پیدا نشد: {attachment}", "path": ""}
        data = src.read_bytes()
        attached_bytes = len(data)
        msg.add_attachment(
            data, maintype="application", subtype="octet-stream", filename=src.name,
        )

    stamp = _now_stamp()
    safe_to = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in to)[:40]
    out_path = _outbox_dir(out_dir) / f"{stamp}-{safe_to}.eml"
    out_path.write_bytes(msg.as_bytes())
    return {
        "ok": True,
        "path": str(out_path),
        "bytes": out_path.stat().st_size,
        "to": to,
        "subject": subject,
        "attachment_bytes": attached_bytes,
        "error": "",
    }


def send(path: str) -> dict[str, Any]:
    """Send a composed .eml through SMTP — only when env credentials exist."""
    src = Path(path)
    if not src.exists():
        return {"ok": False, "error": f"فایل ایمیل پیدا نشد: {path}", "sent": False}
    host = os.environ.get(_ENV_HOST, "")
    if not host:
        return {
            "ok": False,
            "sent": False,
            "error": (
                "فایل ایمیل ساخته شد ولی ارسال نشد — اعتبارنامهی SMTP تنظیم نشده است "
                f"(متغیرهای محیطی {_ENV_HOST} و {_ENV_USER} و {_ENV_PASS})"
            ),
        }
    import smtplib

    port = int(os.environ.get(_ENV_PORT, "587") or 587)
    user = os.environ.get(_ENV_USER, "")
    password = os.environ.get(_ENV_PASS, "")
    try:
        from email import message_from_bytes

        msg = message_from_bytes(src.read_bytes())
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if user:
                smtp.login(user, password)  # credential never echoed
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001 — the real error is named, work kept
        return {"ok": False, "sent": False, "error": f"ارسال ناموفق: {type(exc).__name__}: {exc}"}
    return {"ok": True, "sent": True, "path": str(src), "error": ""}


def _now_stamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d-%H%M%S")


def email_report(
    body: str,
    *,
    to: str = "",
    subject: str = "گزارش ذهن یکپارچه",
    attachment: str = "",
) -> dict[str, Any]:
    """The operator gesture: compose the report and try the optional send."""
    composed = compose(to=to, subject=subject, body=body, attachment=attachment)
    if composed.get("ok") is not True:
        return composed
    sent = send(composed["path"])
    return {
        **composed,
        "sent": sent.get("sent", False),
        "send_note": sent.get("error", ""),
        "ok": True,  # the deliverable (the .eml) EXISTS — the send is a bonus
    }


class EmailToolConnector:
    """Adapts the email outbox to the ``Connector`` protocol."""

    def __init__(self, out_dir: str | None = None) -> None:
        self._out_dir = out_dir

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "compose") or "compose"
        if operation == "compose":
            result = compose(
                to=str(params.get("to") or params.get("address") or ""),
                subject=str(params.get("subject") or "گزارش ذهن یکپارچه"),
                body=str(params.get("body") or ""),
                attachment=str(params.get("attachment") or params.get("path") or ""),
                out_dir=self._out_dir,
            )
        elif operation == "send":
            path = str(params.get("path") or "")
            composed = {"ok": False, "path": path, "error": "no path given"}
            if path:
                result = {"path": path, **send(path)}
            else:
                result = composed
        elif operation == "list":
            # R60 Q6 — «ایمیل‌هایم را نشان بده»: the REAL sent-mail listing,
            # newest first, from the REAL outbox directory.
            from universal_mind.email_outbox import _outbox_dir

            d = _outbox_dir(self._out_dir)
            if not d.exists():
                result = {"ok": True, "emails": [], "count": 0, "outbox": str(d)}
            else:
                rows = sorted(
                    (p for p in d.iterdir() if p.suffix == ".eml"),
                    key=lambda p: p.stat().st_mtime, reverse=True,
                )
                emails = []
                from email.header import decode_header as _dh

                def _decode_hdr(raw: str) -> str:
                    # R60 Q6 — .eml headers are MIME-encoded
                    # (=?utf-8?b?...?=); decoded IN FULL or the listing
                    # shows base64 soup instead of the operator's Persian.
                    try:
                        return "".join(
                            (part.decode(charset or "utf-8", errors="replace")
                             if isinstance(part, bytes) else str(part))
                            for part, charset in _dh(raw)
                        ).strip()
                    except Exception:  # noqa: BLE001 — a bad header must not
                        return raw  # kill the listing; the raw is honest

                for p in rows[:50]:
                    head = {"path": p.name}
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")
                        for line in text.splitlines()[:20]:
                            if line.lower().startswith("subject:"):
                                head["subject"] = _decode_hdr(line[8:].strip())
                            elif line.lower().startswith("to:"):
                                head["to"] = _decode_hdr(line[3:].strip())
                            elif not line.strip() and "subject" in head:
                                break
                        head["mtime"] = p.stat().st_mtime
                    except OSError:
                        pass
                    emails.append(head)
                result = {"ok": True, "emails": emails, "count": len(emails),
                          "outbox": str(d)}
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k != "error"
        })


__all__ = ["EmailToolConnector", "compose", "email_report", "send"]
