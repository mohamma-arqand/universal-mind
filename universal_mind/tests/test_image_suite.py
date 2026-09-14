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