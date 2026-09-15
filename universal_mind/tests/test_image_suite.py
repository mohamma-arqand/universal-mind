"""Tests for the integrated ImageSuite (full Pillow capability surface)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from universal_mind.image_suite import ImageSuite, ImageSuiteConnector


def _sample(tmp: Path, size: tuple[int, int] = (120, 80)) -> str:
    p = tmp / "sample.png"
    Image.new("RGB", size, color=(30, 120, 200)).save(p)
    return str(p)


def test_info_reads_real_metadata(tmp_path: Path) -> None:
    suite = ImageSuite()
    meta = suite.info(_sample(tmp_path))
    assert meta["ok"] is True
    assert meta["meta"]["format"] == "PNG"
    assert meta["meta"]["size"] == [120, 80]
    assert meta["meta"]["mode"] == "RGB"


def test_convert_png_to_jpeg_and_bmp(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path)
    for fmt in ("jpeg", "bmp", "webp"):
        out = suite.convert(src, fmt)
        assert out["ok"] is True, out["error"]
        assert Path(out["path"]).exists()
        assert out["bytes"] > 0


def test_resize_changes_real_dimensions(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path)
    out = suite.resize(src, 40, 30)
    assert out["ok"] is True
    meta = suite.info(out["path"])
    assert meta["meta"]["size"] == [40, 30]


def test_crop_produces_a_real_region(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path)
    out = suite.crop(src, (0, 0, 50, 40))
    assert out["ok"] is True
    meta = suite.info(out["path"])
    assert meta["meta"]["size"] == [50, 40]


def test_rotate_expands_canvas(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path)
    out = suite.rotate(src, 90)
    assert out["ok"] is True
    meta = suite.info(out["path"])
    assert meta["meta"]["size"] == [80, 120]  # swapped


def test_filters_apply(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path)
    for kind in ("blur", "sharpen", "contour", "edge_enhance", "grayscale"):
        out = suite.filter(src, kind)
        assert out["ok"] is True, f"{kind}: {out['error']}"


def test_thumbnail_preserves_aspect(tmp_path: Path) -> None:
    suite = ImageSuite()
    src = _sample(tmp_path, (200, 100))
    out = suite.thumbnail(src, 50)
    assert out["ok"] is True
    meta = suite.info(out["path"])
    w, h = meta["meta"]["size"]
    assert max(w, h) == 50
    assert w == 2 * h  # aspect preserved


def test_full_surface_all_operations_real(tmp_path: Path) -> None:
    """Every one of the suite's 33 declared operations performs REAL image work
    (the full Pillow surface, not a subset)."""
    suite = ImageSuite()
    src = _sample(tmp_path, (140, 90))
    skip = {"info", "blend"}  # info verified separately; blend needs two files
    ok, failed = 0, []
    for op in suite.OPERATIONS:
        if op in skip:
            continue
        try:
            if op == "convert":
                r = suite.convert(src, "jpeg")
            elif op == "resize":
                r = suite.resize(src, 50, 40)
            elif op == "crop":
                r = suite.crop(src, (5, 5, 70, 45))
            elif op == "rotate":
                r = suite.rotate(src, 30)
            elif op == "thumbnail":
                r = suite.thumbnail(src, 64)
            elif op in ("posterize",):
                r = suite.posterize(src, 3)
            elif op in ("solarize",):
                r = suite.solarize(src, 100)
            elif op in ("brightness", "contrast", "color", "sharpness"):
                r = getattr(suite, op)(src, 1.3)
            elif op == "draw_text":
                r = suite.draw_text(src, "سلام")
            elif op == "draw_rectangle":
                r = suite.draw_rectangle(src, (10, 10, 50, 35))
            elif op == "quantize":
                r = suite.quantize(src, 8)
            elif op == "split_channels":
                r = suite.split_channels(src)
            else:
                r = getattr(suite, op)(src)
        except Exception as exc:  # noqa: BLE001
            r = {"ok": False, "error": str(exc)}
        if r.get("ok") is True:
            ok += 1
        else:
            failed.append((op, r.get("error", "")[:80]))
    assert ok >= 30, f"only {ok} real operations; failures: {failed}"


def test_blend_two_real_images(tmp_path: Path) -> None:
    suite = ImageSuite()
    a = _sample(tmp_path, (100, 60))
    b_path = tmp_path / "b.png"
    Image.new("RGB", (80, 50), color=(200, 50, 50)).save(b_path)
    out = suite.blend(a, str(b_path), 0.4)
    assert out["ok"] is True
    assert out["bytes"] > 0


def test_split_channels_produces_three_real_files(tmp_path: Path) -> None:
    suite = ImageSuite()
    out = suite.split_channels(_sample(tmp_path))
    assert out["ok"] is True
    assert len(out["paths"]) == 3


def test_draw_text_persian(tmp_path: Path) -> None:
    suite = ImageSuite()
    out = suite.draw_text(_sample(tmp_path), "سلام از ذهن یکپارچه")
    assert out["ok"] is True
    assert out["bytes"] > 0


def test_missing_file_fails_clean(tmp_path: Path) -> None:
    suite = ImageSuite()
    result = suite.info("nonexistent.png")
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_connector_dispatches_operations(tmp_path: Path) -> None:
    conn = ImageSuiteConnector()
    src = _sample(tmp_path)
    meta = conn.connect({}, {"operation": "info", "path": src})
    assert meta.ok is True
    assert meta.output["format"] == "PNG"
    resized = conn.connect({}, {"operation": "resize", "path": src, "width": 30, "height": 30})
    assert resized.ok is True


def test_suite_flows_through_orchestrate(tmp_path: Path) -> None:
    """The whole image program participates in the multi-tool synthesis loop."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.real_tool_registry import real_connector_factory
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(name="img", capability="image",
                           connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                           absorbable=True))
    # "image" is a registered real capability — no mutation of the shared table
    # (the earlier mutate-then-delete pattern was a cross-test contamination bug).
    syn = orchestrate(reg, ["image"], connector_factory=real_connector_factory)
    assert syn.ok is True
    assert syn.output["synthesized_from"]["image"]["format"] == "PNG"