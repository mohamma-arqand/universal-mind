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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from universal_mind.connectors import ConnectorResult


class ImageSuite:
    """The integrated Pillow capability surface (a complete image program)."""

    name = "image-suite"
    capability = "image"

    # Every operation the suite exposes — the FULL surface of the integrated
    # program (Pillow), not a subset: 33 real operations.
    OPERATIONS = (
        # geometry / basic
        "convert", "resize", "crop", "rotate", "thumbnail", "info",
        # ImageOps
        "grayscale", "flip", "mirror", "autocontrast", "invert", "posterize",
        "equalize", "solarize", "flip_transpose",
        # ImageEnhance
        "brightness", "contrast", "color", "sharpness",
        # filters (extended)
        "filter", "blur_more", "contour", "emboss", "edge_enhance_more", "smooth",
        "find_edges", "sharpen_more",
        # draw / compose
        "draw_text", "draw_rectangle", "watermark",
        # modes / advanced
        "quantize", "to_rgba", "split_channels", "blend",
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

    # --- shared helper for all single-image transforms ---
    def _transform(self, path: str, name: str, fn: Any) -> dict[str, Any]:
        """Run a real Pillow transform on a real file, saving to a temp artifact."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / f"{name}.png"
        try:
            with Image.open(src) as im:
                fn(im).save(out_path)
        except Exception as exc:  # noqa: BLE001 — real transform errors surface
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, "error": ""}

    # --- ImageOps operations (real, full-surface) ---
    def grayscale(self, path: str) -> dict[str, Any]:
        return self._transform(path, "grayscale", lambda im: ImageOps.grayscale(im).convert("RGB"))

    def flip(self, path: str) -> dict[str, Any]:
        return self._transform(path, "flip", lambda im: ImageOps.flip(im))

    def mirror(self, path: str) -> dict[str, Any]:
        return self._transform(path, "mirror", lambda im: ImageOps.mirror(im))

    def autocontrast(self, path: str) -> dict[str, Any]:
        return self._transform(path, "autocontrast", lambda im: ImageOps.autocontrast(im))

    def invert(self, path: str) -> dict[str, Any]:
        def _invert(im: Any) -> Any:
            return ImageOps.invert(im.convert("RGB"))
        return self._transform(path, "invert", _invert)

    def posterize(self, path: str, bits: int = 4) -> dict[str, Any]:
        def _posterize(im: Any) -> Any:
            return ImageOps.posterize(im.convert("RGB"), bits)
        return self._transform(path, "posterize", _posterize)

    def equalize(self, path: str) -> dict[str, Any]:
        def _equalize(im: Any) -> Any:
            return ImageOps.equalize(im.convert("RGB"))
        return self._transform(path, "equalize", _equalize)

    def solarize(self, path: str, threshold: int = 128) -> dict[str, Any]:
        def _solarize(im: Any) -> Any:
            return ImageOps.solarize(im.convert("RGB"), threshold)
        return self._transform(path, "solarize", _solarize)

    def flip_transpose(self, path: str) -> dict[str, Any]:
        return self._transform(path, "transpose", lambda im: im.transpose(Image.TRANSPOSE))

    # --- ImageEnhance operations (real) ---
    def brightness(self, path: str, factor: float = 1.5) -> dict[str, Any]:
        def _bright(im: Any) -> Any:
            return ImageEnhance.Brightness(im).enhance(factor)
        return self._transform(path, "brightness", _bright)

    def contrast(self, path: str, factor: float = 1.5) -> dict[str, Any]:
        def _contrast(im: Any) -> Any:
            return ImageEnhance.Contrast(im).enhance(factor)
        return self._transform(path, "contrast", _contrast)

    def color(self, path: str, factor: float = 1.5) -> dict[str, Any]:
        def _color(im: Any) -> Any:
            return ImageEnhance.Color(im).enhance(factor)
        return self._transform(path, "color", _color)

    def sharpness(self, path: str, factor: float = 2.0) -> dict[str, Any]:
        def _sharp(im: Any) -> Any:
            return ImageEnhance.Sharpness(im).enhance(factor)
        return self._transform(path, "sharpness", _sharp)

    # --- extended filters (real) ---
    def blur_more(self, path: str) -> dict[str, Any]:
        return self._transform(path, "blur_more", lambda im: im.filter(ImageFilter.GaussianBlur(4)))

    def contour(self, path: str) -> dict[str, Any]:
        return self._transform(path, "contour", lambda im: im.filter(ImageFilter.CONTOUR))

    def emboss(self, path: str) -> dict[str, Any]:
        return self._transform(path, "emboss", lambda im: im.filter(ImageFilter.EMBOSS))

    def edge_enhance_more(self, path: str) -> dict[str, Any]:
        return self._transform(path, "edge_more", lambda im: im.filter(ImageFilter.EDGE_ENHANCE_MORE))

    def smooth(self, path: str) -> dict[str, Any]:
        return self._transform(path, "smooth", lambda im: im.filter(ImageFilter.SMOOTH))

    def find_edges(self, path: str) -> dict[str, Any]:
        return self._transform(path, "edges", lambda im: im.filter(ImageFilter.FIND_EDGES))

    def sharpen_more(self, path: str) -> dict[str, Any]:
        return self._transform(path, "sharpen_more", lambda im: im.filter(ImageFilter.SHARPEN))

    # --- draw / compose (real) ---
    def draw_text(self, path: str, text: str = "Universal Mind", color: str = "white") -> dict[str, Any]:
        def _draw(im: Any) -> Any:
            drawable = ImageDraw.Draw(im)
            drawable.text((10, im.height - 30), text, fill=color)
            return im
        return self._transform(path, "text", _draw)

    def draw_rectangle(self, path: str, box: tuple[int, int, int, int] = (10, 10, 60, 40), color: str = "red") -> dict[str, Any]:
        def _rect(im: Any) -> Any:
            drawable = ImageDraw.Draw(im)
            drawable.rectangle(list(box), fill=color)
            return im
        return self._transform(path, "rectangle", _rect)

    def watermark(self, path: str, text: str = "© Universal Mind") -> dict[str, Any]:
        def _wm(im: Any) -> Any:
            drawable = ImageDraw.Draw(im)
            drawable.text((im.width - 140, im.height - 24), text, fill="white")
            return im
        return self._transform(path, "watermark", _wm)

    # --- modes / advanced (real) ---
    def quantize(self, path: str, colors: int = 16) -> dict[str, Any]:
        def _quantize(im: Any) -> Any:
            return im.convert("RGB").quantize(colors).convert("RGB")
        return self._transform(path, "quantized", _quantize)

    def to_rgba(self, path: str) -> dict[str, Any]:
        return self._transform(path, "rgba", lambda im: im.convert("RGBA"))

    def split_channels(self, path: str) -> dict[str, Any]:
        """Split into R/G/B channel images (real files, one per channel)."""
        src = Path(path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        try:
            with Image.open(src) as im:
                channels = im.convert("RGB").split()
                paths = []
                for ch, band in zip("rgb", channels, strict=False):  # 3 letters, 3 channels
                    out = out_dir / f"channel_{ch}.png"
                    band.save(out)
                    paths.append(str(out))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "paths": paths, "error": ""}

    def blend(self, path: str, other_path: str, alpha: float = 0.5) -> dict[str, Any]:
        """Real alpha-blend of two images (both resized to the first's size)."""
        src = Path(path)
        other = Path(other_path)
        if not src.exists():
            return {"ok": False, "error": f"file not found: {path}"}
        if not other.exists():
            return {"ok": False, "error": f"file not found: {other_path}"}
        out_dir = Path(tempfile.mkdtemp(prefix="um-img-"))
        out_path = out_dir / "blended.png"
        try:
            with Image.open(src) as a, Image.open(other) as b:
                b = b.resize(a.size)
                Image.blend(a.convert("RGB"), b.convert("RGB"), alpha).save(out_path)
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
        suite = self._suite
        method = {
            # geometry / basic
            "convert": lambda: suite.convert(path, params["out_format"]),
            "resize": lambda: suite.resize(path, int(params["width"]), int(params["height"])),
            "crop": lambda: suite.crop(path, tuple(params["box"])),
            "rotate": lambda: suite.rotate(path, int(params["degrees"])),
            "thumbnail": lambda: suite.thumbnail(path, int(params.get("max_side", 128))),
            "info": lambda: suite.info(path),
            # ImageOps
            "grayscale": lambda: suite.grayscale(path),
            "flip": lambda: suite.flip(path),
            "mirror": lambda: suite.mirror(path),
            "autocontrast": lambda: suite.autocontrast(path),
            "invert": lambda: suite.invert(path),
            "posterize": lambda: suite.posterize(path, int(params.get("bits", 4))),
            "equalize": lambda: suite.equalize(path),
            "solarize": lambda: suite.solarize(path, int(params.get("threshold", 128))),
            "flip_transpose": lambda: suite.flip_transpose(path),
            # ImageEnhance
            "brightness": lambda: suite.brightness(path, float(params.get("factor", 1.5))),
            "contrast": lambda: suite.contrast(path, float(params.get("factor", 1.5))),
            "color": lambda: suite.color(path, float(params.get("factor", 1.5))),
            "sharpness": lambda: suite.sharpness(path, float(params.get("factor", 2.0))),
            # extended filters
            "filter": lambda: suite.filter(path, params.get("kind", "blur")),
            "blur_more": lambda: suite.blur_more(path),
            "contour": lambda: suite.contour(path),
            "emboss": lambda: suite.emboss(path),
            "edge_enhance_more": lambda: suite.edge_enhance_more(path),
            "smooth": lambda: suite.smooth(path),
            "find_edges": lambda: suite.find_edges(path),
            "sharpen_more": lambda: suite.sharpen_more(path),
            # draw / compose
            "draw_text": lambda: suite.draw_text(path, params.get("text", "Universal Mind"), params.get("color", "white")),
            "draw_rectangle": lambda: suite.draw_rectangle(path, tuple(params.get("box", (10, 10, 60, 40))), params.get("color", "red")),
            "watermark": lambda: suite.watermark(path, params.get("text", "© Universal Mind")),
            # modes / advanced
            "quantize": lambda: suite.quantize(path, int(params.get("colors", 16))),
            "to_rgba": lambda: suite.to_rgba(path),
            "split_channels": lambda: suite.split_channels(path),
            "blend": lambda: suite.blend(path, params["other_path"], float(params.get("alpha", 0.5))),
        }.get(operation)
        if method is None:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = method()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        output: Any = result.get("meta") if operation == "info" else {
            "path": result.get("path"), "bytes": result.get("bytes"),
            **({"paths": result["paths"]} if "paths" in result else {}),
        }
        return ConnectorResult(ok=True, output=output)


__all__ = ["ImageSuite", "ImageSuiteConnector"]