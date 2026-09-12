"""Tests for the real ffmpeg-backed media tool."""

from __future__ import annotations

from unittest.mock import patch

from universal_mind.real_media import MediaTool


def test_available_when_ffmpeg_present() -> None:
    # The host has ffmpeg (verified during development); the method just probes PATH.
    assert MediaTool().available() is True


def test_generate_image_writes_a_real_file() -> None:
    tool = MediaTool()
    result = tool.generate_image()
    assert result["ok"] is True
    assert result["bytes"] > 0
    from pathlib import Path

    assert Path(result["path"]).exists()


def test_missing_ffmpeg_fails_clean() -> None:
    with patch("universal_mind.real_media._ffmpeg", return_value=None):
        result = MediaTool().generate_image()
    assert result["ok"] is False
    assert "not installed" in result["error"]


def test_ffmpeg_error_reports_stderr() -> None:
    with patch("universal_mind.real_media._ffmpeg", return_value="/fake/ffmpeg"):
        result = MediaTool().generate_image()
    assert result["ok"] is False
    assert result["path"] is None


def test_inspect_reads_real_metadata() -> None:
    tool = MediaTool()
    img = tool.generate_image(size="48x24")
    assert img["ok"] is True
    meta = tool.inspect(img["path"])
    assert meta["ok"] is True
    assert meta["meta"]["width"] == 48
    assert meta["meta"]["height"] == 24


def test_inspect_missing_file_fails_clean() -> None:
    tool = MediaTool()
    result = tool.inspect("nonexistent_file_12345.mp4")
    assert result["ok"] is False
    assert "file not found" in result["error"]


def test_transcode_produces_a_real_output() -> None:
    tool = MediaTool()
    img = tool.generate_image()
    assert img["ok"] is True
    out = tool.transcode(img["path"], out_format="png")
    assert out["ok"] is True
    assert out["bytes"] > 0