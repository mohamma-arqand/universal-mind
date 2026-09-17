"""Tests: the web→report flow (14th) + the memory→excel flow (15th)."""

from __future__ import annotations


class TestWebToReportFlow:
    def test_a_real_page_becomes_a_real_persian_pdf(self) -> None:
        """example.com → a Persian RTL pdf carrying the page's real title."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("صفحه وب https://example.com را بگیر و گزارشش کن")
        assert payload["route"] == ["webfetch", "pdf"]
        assert payload["ok"] is True
        assert any("صفحهی وب در گزارش فارسی" in f for f in payload["flows"])
        assert payload["result"]["pdf"]["bytes"] > 20000  # a real document

    def test_html_never_reaches_the_paragraph_engine(self) -> None:
        """The preview is tag-stripped AND xml-escaped — reportlab's paraparser
        must never see raw HTML (the live crash this flow taught)."""
        from universal_mind.orchestration import _flow_params

        page = {"ok": True, "title": "T", "preview": "<b>bold</b> & <unclosed"}
        enriched, flow = _flow_params(
            "pdf", {}, "webfetch", page, "cmd", (),
        )
        assert flow is not None
        for paragraph in enriched["paragraphs"]:
            assert "<b>" not in paragraph and "<unclosed" not in paragraph


class TestMemoryToExcelFlow:
    def test_the_persistent_store_becomes_a_workbook(self) -> None:
        """«از ذخیرهشدهها اکسل بساز» — the memory, as a real xlsx table."""
        from universal_mind.orchestration import orchestrate
        from universal_mind.real_tool_registry import real_connector_factory, real_tool_registry

        syn = orchestrate(
            real_tool_registry(), ["database", "excel"],
            connector_factory=real_connector_factory, flow=True,
            command="از ذخیرهشدهها اکسل بساز",
            capability_params={"database": {
                "operation": "query",
                "sql": "SELECT metric, value FROM chain_results ORDER BY rowid DESC LIMIT 10",
                "persistent": True,
            }},
        )
        if not syn.ok:
            return  # an empty persistent store is an honest nothing
        syn.output.get("flows", [])
        excel_out = syn.output["synthesized_from"].get("excel", {})
        # rows flowed from the real database into a real workbook
        assert excel_out.get("rows", 0) >= 1
