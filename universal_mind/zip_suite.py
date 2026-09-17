"""The Zip suite — the TWENTIETH capability: real zip archives.

Python's zipfile (stdlib) packs and unpacks REAL .zip files — the format the
whole world opens. Unlike the tar.gz chain dossier (archive), this is the
ZIP tool: individual file add, list, and extract, plus a pack-from-list flow
target.

Honest rules:
- A zip with zero real files is a failure, never an empty archive presented
  as success; missing inputs are named.
- Listing reports exactly what the archive contains (name + bytes).
- Extraction refuses to escape the target dir (a zip-slip guard).
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class ZipSuite:
    """A real ZIP program (zipfile): pack/list/extract with a zip-slip guard."""

    name = "zip-suite"
    capability = "zip"

    OPERATIONS = ("pack", "list", "extract")

    def _out(self, out_dir: str | None, name: str) -> Path:
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-zip-"))
        target.mkdir(parents=True, exist_ok=True)
        return target / name

    def pack(self, files: list[str] | None = None, out_dir: str | None = None) -> dict[str, Any]:
        """Pack REAL files into a real .zip (named, counted, sized)."""
        real_files: list[Path] = []
        missing: list[str] = []
        for f in files or []:
            path = Path(f)
            if path.is_file():
                real_files.append(path)
            else:
                missing.append(str(path))
        if not real_files:
            return {
                "ok": False, "error": "فایلی برای بستهبندی نبود",
                "missing": [str(m) for m in missing], "packed": [],
            }
        out_path = self._out(out_dir, "bundle.zip")
        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in real_files:
                    zf.write(path, arcname=path.name)
        except (OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": str(exc), "packed": []}
        return {
            "ok": True, "path": str(out_path), "bytes": out_path.stat().st_size,
            "packed": [p.name for p in real_files],
            "missing": [str(m) for m in missing], "error": "",
        }

    def list_contents(self, path: str) -> dict[str, Any]:
        """The real contents of a zip: names, sizes, count."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "entries": []}
        try:
            with zipfile.ZipFile(src) as zf:
                entries = [
                    {"name": info.filename, "bytes": info.file_size}
                    for info in zf.infolist()
                ]
        except (OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": f"unreadable zip: {exc}", "entries": []}
        return {"ok": True, "entries": entries, "count": len(entries), "error": ""}

    def extract(self, path: str, out_dir: str | None = None) -> dict[str, Any]:
        """Extract a real zip — REFUSING any entry that escapes the target
        (zip-slip: an entry with ../ or an absolute path is skipped, named)."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}", "extracted": []}
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-unzip-"))
        target.mkdir(parents=True, exist_ok=True)
        extracted: list[str] = []
        skipped: list[str] = []
        try:
            with zipfile.ZipFile(src) as zf:
                for info in zf.infolist():
                    name = info.filename
                    dest = (target / name).resolve()
                    if not str(dest).startswith(str(target.resolve())):
                        skipped.append(name)  # zip-slip attempt: named, skipped
                        continue
                    zf.extract(info, target)
                    extracted.append(name)
        except (OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": str(exc), "extracted": extracted}
        return {
            "ok": bool(extracted), "extracted": extracted,
            "skipped": skipped, "target": str(target),
            "error": "" if extracted else "آرشیو خالی بود",
        }


class ZipSuiteConnector:
    """Adapts :class:`ZipSuite` to the ``Connector`` protocol."""

    def __init__(self, suite: ZipSuite | None = None) -> None:
        self._suite = suite if suite is not None else ZipSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "pack") or "pack"
        suite = self._suite
        if operation == "pack":
            result = suite.pack(params.get("files"))
        elif operation == "list":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.list_contents(str(params["path"]))
        elif operation == "extract":
            if not params.get("path"):
                return ConnectorResult(ok=False, output=None, error="no path given")
            result = suite.extract(str(params["path"]))
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k not in ("ok", "error")
        })


__all__ = ["ZipSuite", "ZipSuiteConnector"]