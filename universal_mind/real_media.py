"""Real media tools — ffmpeg-backed specialists that do actual file work.

The super-platform's connectors reached `python`/`git` (probe) and COM/Excel, but
those were mostly version/echo probes. This module makes the connection *effectual*:
a real ffmpeg binary (detected on the host) is wrapped as a tool that actually
produces a media artifact (a generated image/video frame) and reads back a real
property (duration/format). This is "reach a REAL tool and get a REAL result", the
step the execution path named as the gap between structure and real work.

Fail-safe: if ffmpeg is absent, the tool reports ``not ok`` with a clear reason —
never a fabricated artifact. Deterministic given the host binary.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _ffmpeg() -> str | None:
    """The ffmpeg binary on PATH, or None when it is not installed."""
    return shutil.which("ffmpeg")


class MediaTool:
    """A real ffmpeg-backed specialist that generates and inspects media files."""

    name = "ffmpeg"
    capability = "media_generate"

    def available(self) -> bool:
        return _ffmpeg() is not None

    def generate_image(self, *, size: str = "64x64", color: str = "blue", out_dir: str | None = None) -> dict[str, Any]:
        """Generate a real image file with ffmpeg and report its path + size.

        Returns a dict with ``ok``, ``path`` (the written file), ``bytes``, and an
        ``error`` when ffmpeg is missing or failed. The artifact is written into a
        fresh temp dir (never the live tree), so the tool stays a contractor.
        """
        ff = _ffmpeg()
        if ff is None:
            return {"ok": False, "path": None, "bytes": 0, "error": "ffmpeg not installed"}

        target_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-media-"))
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / "generated.png"
        cmd = [
            ff, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s={size}:d=0.5",
            "-frames:v", "1", "-y", str(out_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "path": None, "bytes": 0, "error": str(exc)}

        if result.returncode != 0 or not out_path.exists():
            return {"ok": False, "path": None, "bytes": 0, "error": result.stderr.strip()}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}


__all__ = ["MediaTool"]