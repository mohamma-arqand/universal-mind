"""Real archive tools — gzip/tar-backed specialists that compress a real file.

A second real tool behind the same ``connector_factory`` pattern as the media
tool: instead of media, this one does real file compression. It writes a real
payload and produces a real ``.gz`` archive via the host's gzip/tar, proving the
super-platform can drive *multiple* distinct real effects through one loop.

Fail-safe and isolated: missing binaries or IO errors return ``not ok`` with a
clear reason, and outputs land in a temp dir (never the live tree).
"""

from __future__ import annotations

import gzip
import tempfile
from pathlib import Path
from typing import Any


class ArchiveTool:
    """A real gzip/tar-backed specialist that compresses real payloads."""

    name = "gzip"
    capability = "archive_compress"

    def compress(self, content: str = "Universal Mind payload", out_dir: str | None = None) -> dict[str, Any]:
        """Write a real file and return a real gzip archive of it.

        Returns ``ok``, the archive ``path``, its ``bytes``, and an ``error``.
        Isolation: everything is written into a fresh (or caller-supplied) temp dir.
        """
        target_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-archive-"))
        target_dir.mkdir(parents=True, exist_ok=True)
        raw_path = target_dir / "payload.txt"
        gz_path = target_dir / "payload.txt.gz"
        try:
            raw_path.write_text(content, encoding="utf-8")
            with raw_path.open("rb") as f_in, gzip.open(str(gz_path), "wb") as f_out:
                f_out.write(f_in.read())
        except OSError as exc:
            return {"ok": False, "path": None, "bytes": 0, "error": str(exc)}

        if not gz_path.exists():
            return {"ok": False, "path": None, "bytes": 0, "error": "gzip archive was not produced"}
        return {"ok": True, "path": str(gz_path), "bytes": gz_path.stat().st_size, "error": ""}



    def compress_files(self, files: list[str] | None = None, out_dir: str | None = None) -> dict[str, Any]:
        """Archive REAL produced files of a chain into one .tar.gz bundle.

        The flow target: every artifact the chain made (the chart, the report,
        ...) packed into ONE archive — the run's complete output, preserved.
        Missing files are skipped honestly (listed in 'skipped'); an empty
        or all-missing file set is an honest failure, never a fake archive.
        """
        import tarfile

        target_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-archive-"))
        target_dir.mkdir(parents=True, exist_ok=True)
        archive_path = target_dir / "chain_output.tar.gz"

        existing: list[Path] = []
        skipped: list[str] = []
        for file_str in files or []:
            path = Path(file_str)
            if path.exists():
                existing.append(path)
            else:
                skipped.append(file_str)
        if not existing:
            return {
                "ok": False, "path": None, "bytes": 0,
                "archived": [], "skipped": skipped,
                "error": "هیچ فایل واقعیای برای بایگانی نبود",
            }
        try:
            with tarfile.open(str(archive_path), "w:gz") as tar:
                for path in existing:
                    tar.add(str(path), arcname=path.name)
        except (OSError, tarfile.TarError) as exc:
            return {
                "ok": False, "path": None, "bytes": 0,
                "archived": [], "skipped": skipped, "error": str(exc),
            }
        return {
            "ok": True, "path": str(archive_path), "bytes": archive_path.stat().st_size,
            "archived": [p.name for p in existing], "skipped": skipped, "error": "",
        }


__all__ = ["ArchiveTool"]