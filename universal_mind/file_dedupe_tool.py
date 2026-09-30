"""Real duplicate-file finder — SHA-256 truth, preview-first, no silent deletes.

R53 wave-5: «فایلهای تکراری را پاک کن» needs REAL evidence before any
deletion: two files are duplicates only when their SHA-256 matches — same
size is a candidate, never proof. THE DELETE LAW (the backup rule of this
house): preview mode is the DEFAULT; nothing is deleted unless the operator
explicitly confirms («تأیید کن» or delete=True). Deletion order is honest
(oldest modified kept), every deleted path is recorded for rollback, and a
deletion failure never takes the run down.

Laws:
  - SHA-256 is the ONLY duplicate evidence; size-match is a candidate filter.
  - Preview by default — a tool that deletes on a search verb is a footgun.
  - Each group keeps ONE file (the oldest-modified); the rest are candidates.
  - Unreadable files are skipped AND named, never guessed about.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any

from universal_mind.file_search_tool import _resolve_root  # noqa: F401 — reuse


def _sha256(path: Path, chunk: int = 1024 * 1024) -> str | None:
    """The real digest, or None when the file cannot be read (honest)."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            while True:
                block = fh.read(chunk)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


class FileDedupeTool:
    """A real duplicate finder — SHA-256 evidence, preview-first deletion."""

    name = "filededupe"
    capability = "file_dedupe"

    def find(
        self,
        folder: str | None = None,
        *,
        min_size: int = 1024,
        max_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Find duplicate groups. READ-ONLY: this never deletes anything.

        Returns groups: [{hash, size, files: [paths...], wasted_bytes}],
        where wasted_bytes = size * (len(files) - 1) — the real reclaimable
        number, computed from evidence, never estimated.
        """
        try:
            root = Path(_resolve_root(folder))
        except FileNotFoundError as exc:
            return {"ok": False, "groups": [], "error": f"پوشه پیدا نشد: {exc}"}
        if not root.exists():
            return {"ok": False, "groups": [], "error": f"پوشه پیدا نشد: {root}"}

        deadline = time.monotonic() + max_seconds
        by_size: dict[int, list[str]] = {}
        skipped = 0
        visited = 0
        deadline_hit = False

        walk: list[Path] = [root]
        while walk:
            if time.monotonic() > deadline:
                deadline_hit = True
                break
            current = walk.pop()
            try:
                entries = list(os.scandir(current))
            except OSError:
                skipped += 1
                continue
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in ("$Recycle.Bin", "System Volume Information"):
                            continue
                        walk.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    visited += 1
                    st = entry.stat()
                    if st.st_size >= min_size:
                        by_size.setdefault(st.st_size, []).append(entry.path)
                except OSError:
                    skipped += 1

        # only same-size candidates earn a hash (a different size is never a dup)
        groups: list[dict[str, Any]] = []
        hashed = 0
        for size, paths in by_size.items():
            if len(paths) < 2 or time.monotonic() > deadline:
                if len(paths) >= 2 and time.monotonic() > deadline:
                    deadline_hit = True
                continue
            by_hash: dict[str, list[str]] = {}
            for p in paths:
                digest = _sha256(Path(p))
                hashed += 1
                if digest is None:
                    skipped += 1
                    continue
                by_hash.setdefault(digest, []).append(p)
            for digest, dups in by_hash.items():
                if len(dups) >= 2:
                    groups.append({
                        "hash": digest[:12],
                        "size": size,
                        "files": sorted(dups),
                        "wasted_bytes": size * (len(dups) - 1),
                    })

        groups.sort(key=lambda g: -g["wasted_bytes"])
        total_wasted = sum(g["wasted_bytes"] for g in groups)
        notes: list[str] = []
        if deadline_hit:
            notes.append("زمان پردازش پر شد — نتیجه بخشی از پوشه است")
        if skipped:
            notes.append(f"{skipped} فایل/پوشهی قفلشده خوانده نشد")
        return {
            "ok": True,
            "root": str(root),
            "groups": groups,
            "n_groups": len(groups),
            "wasted_bytes": total_wasted,
            "visited_files": visited,
            "hashed_files": hashed,
            "notes": notes,
            "error": "",
        }

    def clean(
        self,
        folder: str | None = None,
        *,
        confirm: bool = False,
        min_size: int = 1024,
        max_seconds: float = 30.0,
        keep: str = "oldest",
    ) -> dict[str, Any]:
        """THE DELETE PATH — never runs without confirm=True.

        Preview law: find() first; the SAME groups that find() showed are the
        ones deleted (one kept per group). keep='oldest' keeps the
        earliest-modified file of each group (the original), deleting the
        later copies. Every deletion is recorded in `deleted` for rollback.
        """
        report = self.find(folder, min_size=min_size, max_seconds=max_seconds)
        if not report.get("ok"):
            return {**report, "deleted": []}
        if not confirm:
            return {
                **report,
                "deleted": [],
                "preview_only": True,
                "note": (
                    "پیشنمایش — هیچ فایلی حذف نشد. برای حذف واقعی، «تأیید کن» بگو "
                    "یا همان فرمان را دوباره بگو."
                ),
            }
        deleted: list[str] = []
        failed: list[str] = []
        for group in report["groups"]:
            # keep the earliest-modified (the original); delete the rest
            files = sorted(
                group["files"],
                key=lambda p: (Path(p).stat().st_mtime if Path(p).exists() else 0),
            )
            for victim in files[1:]:
                try:
                    os.remove(victim)
                    deleted.append(victim)
                except OSError as exc:
                    failed.append(f"{victim}: {exc}")
        out: dict[str, Any] = {
            "ok": True,
            "deleted": deleted,
            "failed": failed,
            "n_deleted": len(deleted),
            "freed_bytes": sum(group["size"] for group in report["groups"]) if deleted else 0,
            "note": "" if deleted else "چیزی برای حذف نبود (یا همه پیشنمایش بود)",
            "error": "",
        }
        if failed:
            out["note"] = f"{len(failed)} فایل حذف نشد (قفل یا در استفاده)"
        return out


class FileDedupeToolConnector:
    """Adapts :class:`FileDedupeTool` to the ``Connector`` protocol."""

    def __init__(self, tool: FileDedupeTool | None = None) -> None:
        self._tool = tool if tool is not None else FileDedupeTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "find") or "find"
        confirm = bool(params.get("confirm", False) or params.get("delete", False))
        if operation not in ("find", "clean"):
            return ConnectorResult(ok=False, output=None, error=f"عملیات ناشناخته: {operation!r}")
        min_mb = float(params.get("min_size_mb", 0) or 0)
        if operation == "find":
            result = self._tool.find(params.get("folder"), min_size=int(min_mb * 1024 * 1024) or 1024)
        else:
            result = self._tool.clean(
                params.get("folder"), confirm=confirm,
                min_size=int(min_mb * 1024 * 1024) or 1024,
            )
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={k: v for k, v in result.items() if k != "error"})


__all__ = ["FileDedupeTool", "FileDedupeToolConnector"]
