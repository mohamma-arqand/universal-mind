"""Tests: the PDF reader (17th capability) + the pdf-read flow (13th)."""

from __future__ import annotations


class TestPdfReaderTool:
    def test_reads_the_platforms_own_document(self) -> None:
        """A REAL PdfSuite document comes back as real text."""
        from universal_mind.pdf_suite import PdfSuite
        from universal_mind.pdfreader_tool import PdfReaderTool

        written = PdfSuite().document(title="Test Report 42")
        result = PdfReaderTool().read_text(written["path"])
        assert result["ok"] is True
        assert result["pages"] == 1
        assert "Test Report 42" in result["text"]

    def test_missing_file_fails_explicitly(self) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        result = PdfReaderTool().read_text("Z:/no/such.pdf")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_metadata_reads_real_fields(self) -> None:
        from universal_mind.pdf_suite import PdfSuite
        from universal_mind.pdfreader_tool import PdfReaderTool

        written = PdfSuite().document(title="Meta Test")
        result = PdfReaderTool().metadata(written["path"])
        assert result["ok"] is True
        assert result["pages"] >= 1

    def test_connector_contracts(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.pdfreader_tool import PdfReaderToolConnector

        conn = PdfReaderToolConnector()
        no_path = conn.connect({}, {"operation": "read_text"})
        assert isinstance(no_path, ConnectorResult) and no_path.ok is False
        bad_op = conn.connect({}, {"operation": "sign"})
        assert bad_op.ok is False


class TestPdfReadFlow:
    def test_the_chain_reads_its_own_pdf(self) -> None:
        """chart → pdf → pdfreader: the document the chain just wrote is read
        back through the real pypdf engine."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("نمودار خطی بساز و گزارشش کن و پی دی افش را بخوان")
        assert payload["route"] == ["chart", "pdf", "pdfreader"]
        assert payload["ok"] is True
        flows = payload["flows"]
        assert any("→ خواندن PDF" in f for f in flows)
        read_out = payload["result"]["pdfreader"]
        assert read_out["pages"] >= 1  # a real document, really read

    def test_explicit_path_wins(self) -> None:
        from universal_mind.orchestration import _flow_params

        params = {"operation": "read_text", "path": "C:/report.pdf"}
        enriched, flow = _flow_params(
            "pdfreader", params, "pdf", {"ok": True, "path": "other.pdf"}, "cmd", (),
        )
        assert flow is None
        assert enriched["path"] == "C:/report.pdf"
