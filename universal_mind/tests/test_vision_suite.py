"""Tests for the integrated VisionSuite (real OpenCV computer vision)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from universal_mind.vision_suite import VisionSuite, VisionSuiteConnector


def _sample(tmp: Path, rect: bool = True) -> str:
    """A real sample image: a bright rectangle on a dark field (or pure dark)."""
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    if rect:
        image[30:90, 40:120] = (200, 120, 40)
    p = tmp / "sample.png"
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    encoded.tofile(str(p))
    return str(p)


class TestRealVision:
    def test_edges_count_real_pixels(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.edges(_sample(tmp_path))
        assert out["ok"] is True
        # A rectangle-on-dark image has real edges: > 0 edge pixels found.
        assert out["edge_pixels"] > 0
        assert Path(out["path"]).exists()

    def test_grayscale_really_converts(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.grayscale(_sample(tmp_path))
        assert out["ok"] is True
        decoded = cv2.imdecode(np.fromfile(out["path"], dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        assert decoded.ndim == 2  # a real grayscale image has 2 dims

    def test_blur_really_blurs(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        src = _sample(tmp_path)
        original = VisionSuite().stats(src)["stats"]["std"]
        out = suite.blur(src, kernel=15)
        assert out["ok"] is True
        blurred = VisionSuite().stats(out["path"])["stats"]["std"]
        # Gaussian blur reduces contrast: real std drops.
        assert blurred < original

    def test_threshold_reports_real_ratio(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.threshold(_sample(tmp_path), value=50)
        assert out["ok"] is True
        # The rectangle is ~25% of the frame area → the white ratio is near that.
        assert 0.05 < out["white_ratio"] < 0.6

    def test_contours_finds_the_real_rectangle(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.contours(_sample(tmp_path))
        assert out["ok"] is True
        assert out["contour_count"] >= 1
        # The largest contour's area is close to the rectangle's real area (60*80).
        assert out["largest_areas"][0] > 3000

    def test_equalize_produces_real_output(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.equalize(_sample(tmp_path))
        assert out["ok"] is True and out["bytes"] > 0

    def test_flip_and_rotate_and_resize(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        src = _sample(tmp_path)
        assert suite.flip(src, "horizontal")["ok"] is True
        assert suite.flip(src, "vertical")["ok"] is True
        assert suite.flip(src, "magic")["ok"] is False  # honest refusal
        rotated = suite.rotate(src, 90)
        assert rotated["ok"] is True
        resized = suite.resize(src, 50, 50)
        assert resized["ok"] is True

    def test_stats_real_channels(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        out = suite.stats(_sample(tmp_path))
        assert out["ok"] is True
        s = out["stats"]
        assert s["shape"] == [120, 160, 3]
        # The dark field dominates: means are low but non-zero.
        assert 0 < s["mean_b"] < 255

    def test_missing_file_fails_clean(self, tmp_path: Path) -> None:
        suite = VisionSuite()
        result = suite.stats("nonexistent.png")
        assert result["ok"] is False
        assert "not found" in result["error"]


class TestConnector:
    def test_no_params_runs_real_work_on_a_self_generated_sample(self) -> None:
        """A no-params call (as orchestrate issues) runs genuine vision work."""
        conn = VisionSuiteConnector()
        result = conn.connect({}, {})
        assert result.ok is True
        assert result.output["shape"] == [120, 160, 3]

    def test_dispatches_operations(self, tmp_path: Path) -> None:
        conn = VisionSuiteConnector()
        src = _sample(tmp_path)
        edges = conn.connect({}, {"operation": "edges", "path": src})
        assert edges.ok is True and edges.output["edge_pixels"] > 0
        stats = conn.connect({}, {"operation": "stats", "path": src})
        assert stats.ok is True

    def test_unknown_operation_fails_clean(self) -> None:
        conn = VisionSuiteConnector()
        result = conn.connect({}, {"operation": "telepathy"})
        assert result.ok is False
        assert "unknown operation" in result.error

    def test_vision_suite_joins_the_synthesis_loop(self) -> None:
        """The whole vision program participates in the multi-tool synthesis loop."""
        import universal_mind.real_tool_registry as rtr
        from universal_mind.orchestration import orchestrate
        from universal_mind.tool_registry import (
            ConnectionMechanism,
            ToolConnectionSpec,
            ToolEntry,
            ToolRegistry,
        )

        reg = ToolRegistry()
        reg.register(ToolEntry(name="vision", capability="vision",
                               connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                               absorbable=True))
        rtr._REAL_CONNECTORS["vision"] = VisionSuiteConnector  # one-line registration
        try:
            syn = orchestrate(reg, ["vision"], connector_factory=rtr.real_connector_factory)
            assert syn.ok is True
            # The no-params call ran real stats over a self-generated sample.
            assert syn.output["synthesized_from"]["vision"]["shape"] == [120, 160, 3]
        finally:
            del rtr._REAL_CONNECTORS["vision"]