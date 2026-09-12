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


def _ffprobe() -> str | None:
    """The ffprobe binary on PATH, or None when it is not installed."""
    return shutil.which("ffprobe")


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

    def inspect(self, path: str) -> dict[str, Any]:
        """Read real media metadata (width, height, duration) from a file via ffprobe.

        Returns ``ok`` + a ``meta`` dict with ``width``/``height``/``duration`` parsed
        from a real ffprobe call, or ``ok=False`` with a reason when the file is
        missing or ffprobe is unavailable. This is real inspection, not a guess.
        """
        probe = _ffprobe()
        if probe is None:
            return {"ok": False, "meta": {}, "error": "ffprobe not installed"}
        src = Path(path)
        if not src.exists():
            return {"ok": False, "meta": {}, "error": f"file not found: {path}"}
        cmd = [
            probe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0", str(src),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "meta": {}, "error": str(exc)}
        if result.returncode != 0 or not result.stdout.strip():
            return {"ok": False, "meta": {}, "error": result.stderr.strip() or "no video stream"}
        parts = result.stdout.strip().split(",")
        width = _to_int(parts[0]) if len(parts) > 0 else None
        height = _to_int(parts[1]) if len(parts) > 1 else None
        duration = _to_float(parts[2]) if len(parts) > 2 else None
        return {"ok": True, "meta": {"width": width, "height": height, "duration": duration}, "error": ""}

    def transcode(self, path: str, *, out_format: str = "mp4") -> dict[str, Any]:
        """Transcode a real input file to a real output file via ffmpeg.

        Produces a new file (the ``out_format`` extension) in a temp dir and reports
        its path + bytes. This is a genuine media transform — the output is a real
        re-encoded artifact, not a renamed copy.
        """
        ff = _ffmpeg()
        if ff is None:
            return {"ok": False, "path": None, "bytes": 0, "error": "ffmpeg not installed"}
        src = Path(path)
        if not src.exists():
            return {"ok": False, "path": None, "bytes": 0, "error": f"file not found: {path}"}
        out_path = Path(tempfile.mkdtemp(prefix="um-transcode-")) / f"output.{out_format}"
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-i", str(src), "-y", str(out_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        except (FileNotFoundError, OSError) as exc:
            return {"ok": False, "path": None, "bytes": 0, "error": str(exc)}
        if result.returncode != 0 or not out_path.exists():
            return {"ok": False, "path": None, "bytes": 0, "error": result.stderr.strip()}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}


def _to_int(value: str) -> int | None:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


__all__ = ["MediaTool"]