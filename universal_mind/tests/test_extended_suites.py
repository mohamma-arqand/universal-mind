"""Tests for the extended chart + pdf surfaces (full program capability)."""

from __future__ import annotations

from pathlib import Path

from universal_mind.chart_suite import ChartSuite, ChartSuiteConnector
from universal_mind.pdf_suite import PdfSuite, PdfSuiteConnector


class TestExtendedCharts:
    """The 9 new chart operations produce real PNG artifacts."""

    def test_barh(self) -> None:
        out = ChartSuite().barh(["a", "b"], [3, 8])
        assert out["ok"] is True and out["bytes"] > 0

    def test_boxplot(self) -> None:
        out = ChartSuite().boxplot([[1, 2, 3], [2, 3, 4]])
        assert out["ok"] is True

    def test_violin(self) -> None:
        out = ChartSuite().violin([[1, 2, 3], [2, 3, 4]])
        assert out["ok"] is True

    def test_stackplot(self) -> None:
        out = ChartSuite().stackplot({"a": [1, 2], "b": [2, 1]})
        assert out["ok"] is True

    def test_step(self) -> None:
        out = ChartSuite().step({"a": [1, 3, 2]})
        assert out["ok"] is True

    def test_hist2d(self) -> None:
        out = ChartSuite().hist2d([1, 2, 3], [1, 2, 3])
        assert out["ok"] is True

    def test_contour(self) -> None:
        out = ChartSuite().contour()
        assert out["ok"] is True

    def test_errorbar(self) -> None:
        out = ChartSuite().errorbar([1, 2], [2, 4], [0.2, 0.3])
        assert out["ok"] is True

    def test_fill_between(self) -> None:
        out = ChartSuite().fill_between([1, 2], [1, 2], [2, 3])
        assert out["ok"] is True

    def test_connector_dispatches_new_operations(self) -> None:
        conn = ChartSuiteConnector()
        for op in ("barh", "boxplot", "violin", "stackplot", "step", "contour"):
            result = conn.connect({}, {"operation": op})
            assert result.ok is True, f"{op}: {result.error}"


class TestExtendedPdf:
    """The 9 formerly-declared-but-missing PDF operations are now real."""

    def test_multi_page_real_pagination(self) -> None:
        out = PdfSuite().multi_page()
        assert out["ok"] is True
        # A 4-page document must be substantially larger than a 1-pager.
        one = PdfSuite().document(sections=["single"])
        assert out["bytes"] > one["bytes"]

    def test_styled_table_real_grid(self) -> None:
        out = PdfSuite().styled_table()
        assert out["ok"] is True and Path(out["path"]).read_bytes()[:4] == b"%PDF"

    def test_bullet_and_numbered_lists(self) -> None:
        suite = PdfSuite()
        assert suite.bullet_list(["a", "b"])["ok"] is True
        assert suite.numbered_list(["a", "b"])["ok"] is True

    def test_letterhead_and_cover(self) -> None:
        suite = PdfSuite()
        assert suite.letterhead()["ok"] is True
        assert suite.cover_page()["ok"] is True

    def test_invoice_with_total_row(self) -> None:
        out = PdfSuite().invoice([["Item", "Cost"], ["data", "2.0"], ["chart", "3.0"]])
        assert out["ok"] is True

    def test_two_column_and_landscape(self) -> None:
        suite = PdfSuite()
        assert suite.two_column()["ok"] is True
        assert suite.landscape()["ok"] is True

    def test_connector_dispatches_all_declared(self, tmp_path: Path) -> None:
        """Every operation in OPERATIONS dispatches — no declared-but-missing lies."""
        from PIL import Image

        conn = PdfSuiteConnector()
        img = tmp_path / "sample.png"
        Image.new("RGB", (60, 36), color=(50, 50, 200)).save(img)
        for op in PdfSuite.OPERATIONS:
            params: dict = {"operation": op}
            if op == "multi_page":
                params["title"] = "T"
            if op == "with_image":
                params["image_path"] = str(img)
            result = conn.connect({}, params)
            assert result.ok is True, f"{op}: {result.error}"

    def test_unknown_operation_fails_clean(self) -> None:
        conn = PdfSuiteConnector()
        result = conn.connect({}, {"operation": "nonexistent"})
        assert result.ok is False
        assert "unknown operation" in result.error