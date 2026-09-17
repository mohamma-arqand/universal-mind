"""The PDF reader — the SEVENTEENTH capability: the platform reads PDFs.

pypdf extracts the REAL text from real .pdf files (the platform's own
reports included): page count, per-page text, metadata. The closing of the
document loop — the platform WRITES PDFs, and now READS them back.

Honest rules:
- The extracted text is the file's actual content layer — a scanned PDF with
  no text layer returns honestly empty (OCR is a different tool; conflating
  them would be a lie about what happened).
- Missing/corrupt files fail with the exact cause, never an exception leak.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class PdfReaderTool:
    """A real PDF reader (pypdf): text, pages, metadata."""

    name = "pdfreader"
    capability = "pdfreader"

    OPERATIONS = ("read_text", "metadata")

    def read_text(self, path: str, max_chars: int = 20_000) -> dict[str, Any]:
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "text": "", "pages": 0}
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(src))
            chunks: list[str] = []
            total = 0
            for page in reader.pages:
                piece = page.extract_text() or ""
                chunks.append(piece)
                total += len(piece)
                if total >= max_chars:
                    break
            text = "\n".join(chunks)[:max_chars]
            return {
                "ok": True, "text": text, "pages": len(reader.pages),
                "chars": len(text), "truncated": total > max_chars,
                "error": "",
            }
        except ImportError as exc:
            return {"ok": False, "error": f"pypdf unavailable: {exc}", "text": "", "pages": 0}
        except Exception as exc:  # noqa: BLE001 — corrupt pdf, permissions, ...
            return {"ok": False, "error": f"unreadable pdf: {exc}", "text": "", "pages": 0}

    def metadata(self, path: str) -> dict[str, Any]:
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "meta": {}}
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(src))
            info = reader.metadata or {}
            meta = {k.lstrip("/"): str(v) for k, v in dict(info).items()}
            return {"ok": True, "pages": len(reader.pages), "meta": meta, "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"unreadable pdf: {exc}", "meta": {}}


class PdfReaderToolConnector:
    """Adapts :class:`PdfReaderTool` to the ``Connector`` protocol."""

    def __init__(self, tool: PdfReaderTool | None = None) -> None:
        self._tool = tool if tool is not None else PdfReaderTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "read_text") or "read_text"
        path = str(params.get("path", "")).strip()
        if not path:
            return ConnectorResult(ok=False, output=None, error="no path given")
        if operation == "read_text":
            result = self._tool.read_text(path)
        elif operation == "metadata":
            result = self._tool.metadata(path)
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k not in ("ok", "error")
        })


__all__ = ["PdfReaderTool", "PdfReaderToolConnector"]