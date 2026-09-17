"""Tests: the Excel suite (15th capability) + the excel flow (12th)."""

from __future__ import annotations


class TestExcelSuite:
    def test_write_and_read_roundtrip_is_real(self) -> None:
        """A styled workbook with Persian headers reads back exactly."""
        from universal_mind.excel_suite import ExcelSuite

        suite = ExcelSuite()
        written = suite.write_table(
            headers=["شاخص", "مقدار"], rows=[["میانگین", 7.5], ["std", 2.1]]
        )
        assert written["ok"] is True
        assert written["bytes"] > 4000  # a real xlsx, not a stub

        read = suite.read_table(written["path"])
        assert read["ok"] is True
        assert read["headers"] == ["شاخص", "مقدار"]
        assert read["rows"][0] == ["میانگین", 7.5]  # typed values back
        assert read["rows"][1][1] == 2.1

    def test_add_formula_is_honest(self) -> None:
        """The formula text lands in the real cell (openpyxl stores; Excel computes)."""
        from universal_mind.excel_suite import ExcelSuite

        suite = ExcelSuite()
        written = suite.write_table(headers=["A", "B"], rows=[[1, 2], [3, 4]])
        result = suite.add_formula(written["path"], formula="=SUM(B2:B3)", cell="B5")
        assert result["ok"] is True
        back = suite.read_table(written["path"])
        # the formula cell holds the formula string, exactly as written
        flat = [c for row in back["rows"] for c in row]
        assert "=SUM(B2:B3)" in flat

    def test_missing_file_fails_explicitly(self) -> None:
        from universal_mind.excel_suite import ExcelSuite

        result = ExcelSuite().read_table("Z:/no/such.xlsx")
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_connector_dispatches_all_operations(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.excel_suite import ExcelSuiteConnector

        conn = ExcelSuiteConnector()
        write = conn.connect({}, {"operation": "write_table",
                                  "headers": ["x", "y"], "rows": [[1, 2]]})
        assert isinstance(write, ConnectorResult) and write.ok is True
        path = write.output["path"]

        read = conn.connect({}, {"operation": "read_table", "path": path})
        assert read.ok is True and read.output["rows"] == [[1, 2]]

        sheets = conn.connect({}, {"operation": "sheets", "path": path})
        assert sheets.ok is True and sheets.output["sheets"]

        formula = conn.connect({}, {"operation": "add_formula", "path": path,
                                    "formula": "=SUM(A1:A2)", "cell": "D1"})
        assert formula.ok is True

        bad = conn.connect({}, {"operation": "dance"})
        assert bad.ok is False


class TestExcelFlow:
    def test_data_flows_into_a_real_workbook(self) -> None:
        """«حساب کن و در اکسل بریز» — the computed metrics become a real xlsx."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۱۰ و ۲۰ و ۳۰ را حساب کن و در اکسل بریز")
        assert payload["route"] == ["data", "excel"]
        assert payload["ok"] is True
        assert any("→ excel" in f for f in payload["flows"])
        excel_out = payload["result"]["excel"]
        assert excel_out["rows"] == 6  # the six computed metrics, named
        assert excel_out["columns"] == 2
        assert excel_out["bytes"] > 4000

    def test_explicit_read_is_never_overridden(self) -> None:
        """«اکسل X را بخوان» with a path reads THAT workbook."""
        from universal_mind.excel_suite import ExcelSuite
        from universal_mind.orchestration import _flow_params

        suite = ExcelSuite()
        written = suite.write_table(headers=["k", "v"], rows=[[1, 2]])
        params = {"operation": "read_table", "path": written["path"]}
        enriched, flow = _flow_params(
            "excel", params, "data", {"ok": True, "mean": 5.0}, "cmd", (),
        )
        assert flow is None  # the read intent stands, untouched
        assert enriched["path"] == written["path"]

    def test_the_report_narrates_the_workbook(self) -> None:
        from universal_mind.persian_report import persian_report
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۴ و ۶ را حساب کن و در اکسل بریز")
        report = persian_report(payload)
        assert "صفحهگستردهی اکسل ساخته شد" in report
        assert "ردیف" in report and "excel" not in report  # Persian, no leak
