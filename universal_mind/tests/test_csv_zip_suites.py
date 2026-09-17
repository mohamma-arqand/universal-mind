"""Tests: the CSV suite (19th) + Zip suite (20th) + their flows (18th/19th)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class TestCsvSuite:
    def test_write_and_read_roundtrip_with_types(self) -> None:
        from universal_mind.csv_suite import CsvSuite

        suite = CsvSuite()
        written = suite.write_table(headers=["شاخص", "مقدار"], rows=[["میانگین", 7.5], ["std", 2]])
        assert written["ok"] is True and written["bytes"] > 20
        read = suite.read_table(written["path"])
        assert read["headers"] == ["شاخص", "مقدار"]
        assert read["rows"][0] == ["میانگین", 7.5]  # float STAYS float
        assert read["rows"][1][1] == 2  # int parsed

    def test_missing_file_fails_explicitly(self) -> None:
        from universal_mind.csv_suite import CsvSuite

        result = CsvSuite().read_table("Z:/no.csv")
        assert result["ok"] is False and "not found" in result["error"]

    def test_connector_contracts(self) -> None:
        from universal_mind.connectors import ConnectorResult
        from universal_mind.csv_suite import CsvSuiteConnector

        conn = CsvSuiteConnector()
        write = conn.connect({}, {"operation": "write_table", "headers": ["x"], "rows": [[1]]})
        assert isinstance(write, ConnectorResult) and write.ok
        no_path = conn.connect({}, {"operation": "read_table"})
        assert no_path.ok is False
        bad = conn.connect({}, {"operation": "spin"})
        assert bad.ok is False


class TestZipSuite:
    def test_pack_list_extract_roundtrip(self) -> None:
        from universal_mind.csv_suite import CsvSuite
        from universal_mind.zip_suite import ZipSuite

        folder = tempfile.mkdtemp(prefix="um-ziptest-")
        csv_path = CsvSuite().write_table(headers=["x"], rows=[[1]], out_dir=folder)["path"]
        packed = ZipSuite().pack([csv_path], out_dir=folder)
        assert packed["ok"] is True and packed["packed"] == ["table.csv"]

        listed = ZipSuite().list_contents(packed["path"])
        assert listed["ok"] is True and listed["entries"][0]["name"] == "table.csv"

        extracted = ZipSuite().extract(packed["path"], out_dir=os.path.join(folder, "out"))
        assert extracted["ok"] is True
        assert Path(extracted["target"], "table.csv").exists()

    def test_empty_pack_is_honest_failure(self) -> None:
        from universal_mind.zip_suite import ZipSuite

        result = ZipSuite().pack([])
        assert result["ok"] is False
        assert "فایلی" in result["error"]

    def test_zip_slip_is_refused_and_named(self) -> None:
        """A malicious entry path (../escape) is SKIPPED and NAMED — the guard."""
        import tempfile
        import zipfile

        from universal_mind.zip_suite import ZipSuite

        folder = Path(tempfile.mkdtemp(prefix="um-slip-"))
        evil = folder / "evil.zip"
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr("../escaped.txt", "bad")
            zf.writestr("safe.txt", "good")
        result = ZipSuite().extract(str(evil), out_dir=str(folder / "target"))
        assert any(s.endswith("escaped.txt") for s in result["skipped"])
        assert "safe.txt" in result["extracted"]
        assert not (folder / "escaped.txt").exists()


class TestCsvAndZipFlows:
    def test_data_flows_into_a_real_csv(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۸ و ۱۲ را حساب کن و در سیاسوی بریز")
        assert payload["route"] == ["data", "csv"]
        assert any("→ csv" in f for f in payload["flows"])
        csv_out = payload["result"]["csv"]
        assert csv_out["rows"] == 6 and csv_out["bytes"] > 40

    def test_csv_then_zip_in_one_chain(self) -> None:
        """data → csv → zip: the chain's csv file lands inside a real zip."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۸ و ۱۲ را حساب کن و در سیاسوی بریز و زیپش کن")
        assert payload["route"] == ["data", "csv", "zip"]
        assert payload["ok"] is True
        flows = payload["flows"]
        assert any("→ csv" in f for f in flows)
        assert any("→ zip" in f for f in flows)
        assert payload["result"]["zip"]["packed"] == ["table.csv"]

    def test_zip_word_no_longer_fires_archive(self) -> None:
        """«زیپ» means zip — the archive capability keeps its own words."""
        from universal_mind.persian_router import route

        assert "zip" in route("زیپش کن").capabilities
        assert "archive" in route("بایگانی کن").capabilities
        assert "zip" not in route("بایگانی کن").capabilities
