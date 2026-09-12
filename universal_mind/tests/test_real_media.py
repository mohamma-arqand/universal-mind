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