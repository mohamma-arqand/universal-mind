"""R74 P3 — the FOLDER PACK helper for the zip suite.

«پوشه X را زیپ کن» — the folder's real files (not the folder name as a
single string, which pack() would reject as a missing file). Every file
is named; an empty folder is an honest named refusal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def pack_folder(folder: Path) -> dict[str, Any]:
    """Resolve a folder ask into pack params: files=the folder's real files."""
    if not folder.exists():
        return {"operation": "pack",
                "error": f"پوشه پیدا نشد: {folder}"}
    files = [str(f) for f in sorted(folder.rglob("*")) if f.is_file()]
    if not files:
        return {"operation": "pack",
                "error": f"پوشه «{folder}» خالی است — چیزی برای بستهبندی نیست"}
    return {"operation": "pack", "files": files}
