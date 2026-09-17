"""Tests: the web→excel flow (16th) + the ocr→database flow (17th)."""

from __future__ import annotations


class TestWebToExcelFlow:
    def test_a_fetched_page_becomes_a_real_workbook(self) -> None:
        """صفحه وب → در اکسل: the page's real text, as a real xlsx."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("صفحه وب https://example.com را بگیر و در اکسل بریز")
        assert payload["route"] == ["webfetch", "excel"]
        assert payload["ok"] is True
        assert any("→ excel" in f for f in payload["flows"])
        excel_out = payload["result"]["excel"]
        assert excel_out["rows"] >= 5  # the page's real words as rows
        assert excel_out["bytes"] > 4000

    def test_a_url_is_never_treated_as_a_workbook_path(self) -> None:
        """The live bug this flow caught: 's://example.com' was taken as an
        xlsx path. URLs belong to webfetch, never to a workbook read."""
        from universal_mind.persian_params import extract_params

        params = extract_params("صفحه وب https://example.com را بگیر و در اکسل بریز", "excel")
        assert params.get("operation") != "read_table"


class TestOcrToDatabaseFlow:
    def test_read_text_persists_as_memory(self) -> None:
        """متن تصویر بخوان و ذخیره کن: what was READ lands in the real store."""
        import os
        import tempfile

        from PIL import Image, ImageDraw

        folder = tempfile.mkdtemp(prefix="um-ocr-db-test-")
        img_path = os.path.join(folder, "note.png")
        img = Image.new("RGB", (460, 130), "white")
        ImageDraw.Draw(img).text((25, 45), "HELLO OCR WORLD 42", fill="black")
        img.save(img_path)

        from universal_mind.persian_router import route_and_run

        payload = route_and_run(f"متن تصویر {img_path} را بخوان و در دیتابیس ذخیره کن")
        assert payload["route"] == ["ocr", "database"]
        assert payload["ok"] is True
        flows = payload["flows"]
        assert any("→ database" in f for f in flows)
        assert "واژهی خواندهشده" in flows[0]

    def test_the_database_sink_regression_is_locked(self) -> None:
        """database MUST be a sink (last) — a regression once dropped it and
        every database chain reversed its order silently."""
        from universal_mind.dependency_planner import plan_chain

        plan = plan_chain(["database", "data"])
        caps = [s.capability for s in plan.steps]
        assert caps == ["data", "database"]
