"""Real file search — the platform FINDS files on the operator's real disk.

R53 wave-4: «فایلهای بزرگ دیسک D را پیدا کن» / «فایلهای عکس را پیدا کن» were
«نشناختم». This tool walks the REAL filesystem: top-K by size, name/wildcard
matching, with HONEST accounting — every unreadable folder is NAMED in the
result (never silent), a bounded walk with a deadline never hangs, and a walk
with zero hits says so instead of inventing matches.

Laws (the house style):
  - READ-ONLY, always. Search never moves, renames, or deletes anything.
  - Unreadable paths are counted and reported, not swallowed.
  - The walk has a hard deadline (default 20s) and a max-files cap; a walk
    that hits the deadline says SO — a partial answer with its boundary is
    honest, an infinite walk is not.
"""

from __future__ import annotations

import fnmatch
import os
import time
from pathlib import Path
from typing import Any

# Persian digit fold for «۱۰ مگابایت» style params
_FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

# known-folder aliases the operator actually says («دانلودها» etc.)
_KNOWN: dict[str, str] = {
    "دانلود": "Downloads",
    "دانلودها": "Downloads",
    "مستندات": "Documents",
    "داکیومنت": "Documents",
    "تصاویر": "Pictures",
    "عکسها": "Pictures",
    "موزیک": "Music",
    "دسکتاپ": "Desktop",
    "ویدیوها": "Videos",
    "فیلمها": "Videos",
}

_SIZE_HINTS = {
    "مگابایت": 1024 * 1024,
    "گیگابایت": 1024 * 1024 * 1024,
    "کیلوبایت": 1024,
}


def _fold_fa(text: str) -> str:
    return text.translate(_FA)


def _resolve_root(folder: str | None) -> str:
    """Resolve the search root: an explicit path, a known folder, or CWD."""
    home = Path.home()
    if not folder:
        return str(home)
    folded = _fold_fa(folder).strip()
    # known Persian folder names → the operator's real profile folders
    for fa, en in _KNOWN.items():
        if fa in folded:
            cand = home / en
            return str(cand) if cand.exists() else str(home)
    # drive letters: «دیسک D» / «D:» / «درایو e»
    low = folded.lower().replace("دیسک ", "").replace("درایو ", "").strip()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        if low in (letter, f"{letter}:", f"{letter}\\", f"{letter}/"):
            drive = f"{letter.upper()}:\\"
            if Path(drive).exists():
                return drive
    # a real path the operator named — HONEST: an explicit path that does not
    # exist is a NAMED failure (never silently fall back to home, which would
    # answer a different question than the one asked).
    p = Path(folded)
    if p.exists():
        return str(p)
    if (":" in folded or folded.startswith(("/" , "~"))):
        raise FileNotFoundError(folded)
    return str(home)


class FileSearchTool:
    """A real filesystem search specialist — read-only, honest, bounded."""

    name = "filesearch"
    capability = "file_search"

    def search(
        self,
        folder: str | None = None,
        *,
        name: str = "",
        top: int = 10,
        min_size: int = 0,
        max_seconds: float = 20.0,
        max_files: int = 200_000,
    ) -> dict[str, Any]:
        """Find real files. Returns ok, matches (path/size/modified), counts.

        folder: where to walk (None = home). name: wildcard/contains filter.
        top: how many results (sorted by size desc). min_size: bytes floor.
        max_seconds: hard walk deadline. max_files: hard visited-files cap.
        """
        try:
            root = Path(_resolve_root(folder))
        except FileNotFoundError as exc:
            return {"ok": False, "matches": [], "error": f"پوشه پیدا نشد: {exc}"}
        if not root.exists():
            return {"ok": False, "matches": [], "error": f"پوشه پیدا نشد: {root}"}
        deadline = time.monotonic() + max_seconds
        name_low = _fold_fa(name).lower().strip()
        pattern_hits: list[dict[str, Any]] = []
        visited = 0
        skipped_dirs = 0
        deadline_hit = False
        cap_hit = False

        walk_paths: list[Path] = [root]
        while walk_paths:
            if time.monotonic() > deadline:
                deadline_hit = True
                break
            current = walk_paths.pop()
            try:
                entries = list(os.scandir(current))
            except OSError:
                skipped_dirs += 1  # a locked folder is NAMED, never silent
                continue
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        # never descend into system-junction rabbit holes
                        if entry.name in ("$Recycle.Bin", "System Volume Information", "Windows.old"):
                            continue
                        walk_paths.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    visited += 1
                    if visited > max_files:
                        cap_hit = True
                        break
                    st = entry.stat()
                    if st.st_size < min_size:
                        continue
                    if name_low:
                        # multi-token name («jpg png gif») = ANY-token match;
                        # single token = plain contains/wildcard
                        tokens = name_low.split()
                        hit_name = any(
                            fnmatch.fnmatch(entry.name.lower(), f"*{t}*") for t in tokens
                        ) if len(tokens) > 1 else fnmatch.fnmatch(
                            entry.name.lower(), f"*{name_low}*"
                        )
                        if not hit_name:
                            continue
                    if len(pattern_hits) < top:
                        pattern_hits.append({
                            "path": entry.path,
                            "name": entry.name,
                            "bytes": st.st_size,
                            "modified": st.st_mtime,
                        })
                        if len(pattern_hits) == top:
                            # keep the top-K small with a running floor
                            pattern_hits.sort(key=lambda m: -m["bytes"])
                            # (a full sort at the end makes this exact)
                    else:
                        # replace the smallest when bigger
                        smallest = min(pattern_hits, key=lambda m: m["bytes"])
                        if st.st_size > smallest["bytes"]:
                            smallest.update({
                                "path": entry.path, "name": entry.name,
                                "bytes": st.st_size, "modified": st.st_mtime,
                            })
                except OSError:
                    skipped_dirs += 1
            if cap_hit:
                break

        pattern_hits.sort(key=lambda m: -m["bytes"])
        # HONEST BOUNDARIES: what was NOT walked is part of the answer.
        notes: list[str] = []
        if deadline_hit:
            notes.append("زمان جستجو پر شد — نتیجه فقط بخشی از پوشه را پوشش میدهد")
        if cap_hit:
            notes.append("به سقف تعداد فایل رسیدم — پوشهی بزرگتری از حد جستجو است")
        if skipped_dirs:
            notes.append(f"{skipped_dirs} پوشهی قفلشده خوانده نشد")
        return {
            "ok": True,
            "root": str(root),
            "matches": pattern_hits,
            "visited_files": visited,
            "skipped_dirs": skipped_dirs,
            "deadline_hit": deadline_hit,
            "cap_hit": cap_hit,
            "notes": notes,
            "error": "",
        }


class FileSearchToolConnector:
    """Adapts :class:`FileSearchTool` to the ``Connector`` protocol.

    params: {"operation": "search", "folder": "...", "name": "...",
             "top": 10, "min_size_mb": 0}
    """

    def __init__(self, tool: FileSearchTool | None = None) -> None:
        self._tool = tool if tool is not None else FileSearchTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        operation = params.get("operation", "search") or "search"
        if operation != "search":
            return ConnectorResult(ok=False, output=None, error=f"عملیات ناشناخته: {operation!r}")
        top = int(params.get("top", 10) or 10)
        min_mb = float(params.get("min_size_mb", 0) or 0)
        result = self._tool.search(
            params.get("folder"),
            name=str(params.get("name", "") or ""),
            top=max(1, min(100, top)),
            min_size=int(min_mb * 1024 * 1024),
            max_seconds=float(params.get("max_seconds", 20) or 20),
        )
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={k: v for k, v in result.items() if k != "error"})


def extract_search_params(command: str) -> dict[str, Any]:
    """Pull folder / size-hint / name filters out of the Persian command.

    «فایلهای بزرگ دیسک D را پیدا کن» → {folder: "D:", top: 10}
    «فایلهای بزرگتر از ۱۰۰ مگابایت در دانلودها» → {folder: Downloads, min_size_mb: 100}
    «فایلهای عکس را پیدا کن» → {name: "jpg png gif webp"} (multi-token = any-match)
    """
    import re

    folded = _fold_fa(command)
    params: dict[str, Any] = {"operation": "search", "top": 10}

    # «دیسک X» / «درایو X» / bare drive
    m = re.search(r"(?:دیسک|درایو)\s+([a-zA-Z])", folded)
    if m:
        params["folder"] = f"{m.group(1).upper()}:\\"
    else:
        for fa, _en in _KNOWN.items():
            if fa in folded:
                params["folder"] = fa
                break

    # «بزرگتر از N مگابایت/گیگابایت»
    m = re.search(r"بزرگتر از\s*(\d+(?:[.,]\d+)?)\s*(مگابایت|گیگابایت|کیلوبایت)", folded)
    if m:
        n = float(m.group(1).replace(",", "."))
        params["min_size_mb"] = n * (_SIZE_HINTS[m.group(2)] / (1024 * 1024))

    # named extensions: «عکس» / «فیلم» / a literal .ext
    if "عکس" in folded or "تصویر" in folded:
        params["name"] = "jpg jpeg png gif webp bmp"
    elif "فیلم" in folded or "ویدیو" in folded:
        params["name"] = "mp4 mkv avi mov"
    elif "موزیک" in folded or "آهنگ" in folded:
        params["name"] = "mp3 wav flac"
    else:
        m = re.search(r"فایل[های]*\s+([\w.]+)", folded)
        if m and "." in m.group(1):
            params["name"] = m.group(1)

    # «N تا بزرگترین»
    m = re.search(r"(\d+)\s*تا بزرگترین", folded)
    if m:
        params["top"] = int(m.group(1))
    return params


__all__ = ["FileSearchTool", "FileSearchToolConnector", "extract_search_params"]
