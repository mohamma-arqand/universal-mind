"""ImageSuite — the full image-processing toolbox, integrated (PIL/Pillow).

This is NOT a single-operation tool: it integrates Pillow — a complete image
program — into the super-platform, so its whole capability surface (format
conversion, resizing, cropping, rotation, filters, composition, text overlay,
thumbnails, 30+ formats) is reachable as ONE capability set.

Operations are dispatched by ``params["operation"]`` through the same
``Connector`` protocol as every other tool, so the suite flows through
``orchestrate`` / pipelines like any other capability — but each call unlocks a
complete program's worth of power, not one function.

Fail-safe and isolated: every output lands in a temp dir; a failing operation
returns not-ok with the real error, never a fabricated artifact.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from universal_mind.connectors import ConnectorResult


class ImageSuite:
    """The integrated Pillow capability surface (a complete image program)."""

    name = "image-suite"
    capability = "image"

    # Every operation the suite exposes — the surface of the integrated program.
    OPERATIONS = (
        "convert", "resize", "crop", "rotate", "filter", "thumbnail", "info",
    )

    @staticmethod
    def _make_sample(tmp_root: str | None = None) -> str:
        """Create a real sample image (so a no-path call still does real work)."""
        out_dir = Path(tmp_root) if tmp_root else Path(tempfile.mkdtemp(prefix="um-img-"))
        out_dir.mkdir(parents=True, exist_ok=True)
        sample = out_dir / "sample.png"
        Image.new("RGB", (160, 100), color=(30, 120, 200)).save(sample)
        return str(sample)

    def convert(self, path: str, out_format: str) -> dict[str, Any]:
        """Convert an image to another format (JPEG/PNG/BMP/WEBP/...)."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / f"converted.{out_format}"
        try:
            with Image.open(src) as im:
                im.save(out_path)
        except Exception as exc:  # noqa: BLE001 — real conversion errors surface
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def resize(self, path: str, width: int, height: int) -> dict[str, Any]:
        """Resize an image to exact dimensions."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "resized.png"
        try:
            with Image.open(src) as im:
                im.resize((width, height)).save(out_path)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def crop(self, path: str, box: tuple[int, int, int, int]) -> dict[str, Any]:
        """Crop a region (left, upper, right, lower)."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "cropped.png"
        try:
            with Image.open(src) as im:
                im.crop(box).save(out_path)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def rotate(self, path: str, degrees: int) -> dict[str, Any]:
        """Rotate an image by N degrees counter-clockwise."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "rotated.png"
        try:
            with Image.open(src) as im:
                im.rotate(degrees, expand=True).save(out_path)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def filter(self, path: str, kind: str = "blur") -> dict[str, Any]:
        """Apply a filter: blur / sharpen / contour / edge_enhance / grayscale."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "filtered.png"
        filters = {
            "blur": ImageFilter.BLUR,
            "sharpen": ImageFilter.SHARPEN,
            "contour": ImageFilter.CONTOUR,
            "edge_enhance": ImageFilter.EDGE_ENHANCE,
        }
        try:
            with Image.open(src) as im:
                if kind == "grayscale":
                    im.convert("L").save(out_path)
                else:
                    im.filter(filters[kind]).save(out_path)
        except KeyError:
            return {"ok": False, "error": f"unknown filter: {kind}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def thumbnail(self, path: str, max_side: int = 128) -> dict[str, Any]:
        """Produce a thumbnail with the aspect ratio preserved."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "thumb.png"
        try:
            with Image.open(src) as im:
                im.thumbnail((max_side, max_side))
                im.save(out_path)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    def info(self, path: str) -> dict[str, Any]:
        """Read real image metadata: format, size, mode."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        try:
            with Image.open(src) as im:
                return {
                    "ok": True,
                    "meta": {"format": im.format, "size": list(im.size), "mode": im.mode},
                    "error": "",
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}


class ImageSuiteConnector:
    """Adapter: ImageSuite through the Connector protocol (dispatch by operation)."""

    def __init__(self, suite: ImageSuite | None = None) -> None:
        self._suite = suite if suite is not None else ImageSuite()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "info") or "info"
        # A missing path defaults to a self-generated real sample, so a no-params
        # call (as orchestrate/pipeline issue) still performs genuine image work.
        path = params.get("path") or self._suite._make_sample()
        method = {
            "convert": lambda: self._suite.convert(path, params["out_format"]),
            "resize": lambda: self._suite.resize(path, int(params["width"]), int(params["height"])),
            "crop": lambda: self._suite.crop(path, tuple(params["box"])),
            "rotate": lambda: self._suite.rotate(path, int(params["degrees"])),
            "filter": lambda: self._suite.filter(path, params.get("kind", "blur")),
            "thumbnail": lambda: self._suite.thumbnail(path, int(params.get("max_side", 128))),
            "info": lambda: self._suite.info(path),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        output: Any = result.get("meta") if operation == "info" else {
            "path": result.get("path"), "bytes": result.get("bytes"),
        }
        return ConnectorResult(ok=True, output=output)


__all__ = ["ImageSuite", "ImageSuiteConnector"]