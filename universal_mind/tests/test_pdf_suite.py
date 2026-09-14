"""Tests for the integrated PdfSuite (full reportlab capability surface)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from universal_mind.pdf_suite import PdfSuite, PdfSuiteConnector


def test_document_builds_a_real_pdf() -> None:
    suite = PdfSuite()
    out = suite.document(title="Quarterly Report", sections=["Revenue up", "Costs down"])
    assert out["ok"] is True
    p = Path(out["path"])
    assert p.exists() and p.suffix == ".pdf"
    # A real PDF starts with the %PDF magic bytes.
    assert p.read_bytes()[:4] == b"%PDF"


def test_table_builds_a_real_pdf() -> None:
    suite = PdfSuite()
    out = suite.table(headers=["Name", "Score"], rows=[["alice", "9"], ["bob", "7"]])
    assert out["ok"] is True
    assert Path(out["path"]).read_bytes()[:4] == b"%PDF"


def test_with_image_embeds_a_real_file() -> None:
    suite = PdfSuite()
    img = Path(suite.document()["path"]).parent / "sample.png"
    Image.new("RGB", (300, 180), color=(200, 30, 30)).save(img)
    out = suite.with_image(str(img), caption="Telemetry chart")
    assert out["ok"] is True
    assert Path(out["path"]).read_bytes()[:4] == b"%PDF"


def test_with_image_missing_file_fails_clean() -> None:
    suite = PdfSuite()
    out = suite.with_image("nonexistent.png")
    assert out["ok"] is False
    assert "not found" in out["error"]


def test_connector_dispatches_operations() -> None:
    conn = PdfSuiteConnector()
    doc = conn.connect({}, {"operation": "document", "title": "T", "sections": ["s"]})
    assert doc.ok is True and doc.output["bytes"] > 0
    table = conn.connect({}, {"operation": "table"})
    assert table.ok is True


def test_pdf_suite_joins_the_synthesis_loop() -> None:
    """The whole PDF program participates in the multi-tool synthesis loop."""
    import universal_mind.real_tool_registry as rtr
    from universal_mind.orchestration import orchestrate
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    reg.register(ToolEntry(name="pdf", capability="pdf",
                           connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                           absorbable=True))
    rtr._REAL_CONNECTORS["pdf"] = PdfSuiteConnector  # one-line registration
    try:
        syn = orchestrate(reg, ["pdf"], connector_factory=rtr.real_connector_factory)
        assert syn.ok is True
        assert syn.output["synthesized_from"]["pdf"]["bytes"] > 0
    finally:
        del rtr._REAL_CONNECTORS["pdf"]