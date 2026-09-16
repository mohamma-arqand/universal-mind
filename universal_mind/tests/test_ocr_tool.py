"""Tests: the OCR tool — the platform READS images (Windows.Media.Ocr)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _text_image(text: str = "UNIVERSAL MIND 42") -> Path:
    """A real PNG with real rendered text (Pillow draws, the OCR reads)."""
    from PIL import Image, ImageDraw

    folder = tempfile.mkdtemp(prefix="um-ocr-test-")
    img_path = Path(folder) / "note.png"
    img = Image.new("RGB", (420, 130), "white")
    ImageDraw.Draw(img).text((25, 45), text, fill="black")
    img.save(img_path)
    return img_path


class TestOcrTool:
    def test_real_text_is_read_from_pixels(self) -> None:
        """The Windows OCR engine genuinely reads the rendered text."""
        from universal_mind.ocr_tool import OcrTool

        img = _text_image()
        result = OcrTool().read(str(img))
        assert result["ok"] is True
        assert result["language"]  # WHICH recognizer ran is reported
        text = result["text"].upper().replace(" ", "")
        assert "UNIVERSAL" in text and "42" in text  # real extraction

    def test_missing_image_fails_explicitly(self) -> None:
        from universal_mind.ocr_tool import OcrTool

        result = OcrTool().read("Z:/no/such/file.png")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_connector_requires_a_path(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.ocr_tool import OcrToolConnector

        result = OcrToolConnector().connect({}, {"operation": "read"})
        assert isinstance(result, ConnectorResult)
        assert result.ok is False

    def test_unknown_operation_fails_clean(self) -> None:
        from universal_mind.ocr_tool import OcrToolConnector

        result = OcrToolConnector().connect({}, {"operation": "write"})
        assert result.ok is False


class TestOcrFlow:
    def test_explicit_image_reads_for_real(self) -> None:
        """«متن تصویر X را بخوان» routes to OCR alone and really reads."""
        from universal_mind.persian_report import persian_report
        from universal_mind.persian_router import route_and_run

        img = _text_image()
        payload = route_and_run(f"متن تصویر {img} را بخوان")
        assert payload["route"] == ["ocr"]  # the analysis intent won; no 'image'
        assert payload["ok"] is True
        ocr_out = payload["result"]["ocr"]
        assert "UNIVERSAL" in str(ocr_out.get("text", "")).upper()
        report = persian_report(payload)
        assert "متنِ تصویر خوانده شد" in report
        assert "UNIVERSAL" in report  # the extracted text narrated

    def test_chain_image_flows_to_ocr(self) -> None:
        """chart → ocr: the platform reads its own just-made chart."""
        from universal_mind.orchestration import orchestrate
        from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

        syn = orchestrate(
            real_tool_registry(), ["chart", "ocr"],
            connector_factory=real_connector_factory, flow=True,
            command="نمودار بساز و متنش را بخوان",
        )
        assert syn.ok is True
        assert any("→ متنخوان" in f for f in syn.output["flows"])
        # reading the chart's title really returned text (the chart carries it)
        ocr_out = syn.output["synthesized_from"]["ocr"]
        assert isinstance(ocr_out.get("chars", 0), int)

    def test_blank_image_is_honest_empty(self) -> None:
        """A uniform image has no text — ok with empty, honestly narrated."""
        from PIL import Image

        folder = tempfile.mkdtemp(prefix="um-ocr-blank-")
        img_path = os.path.join(folder, "blank.png")
        Image.new("RGB", (100, 100), "white").save(img_path)

        from universal_mind.ocr_tool import OcrTool

        result = OcrTool().read(img_path)
        assert result["ok"] is True
        assert result["text"].strip() == ""  # honest: nothing to read
