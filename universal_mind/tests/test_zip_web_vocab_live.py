"""Tests: the zip/web/vocab LIVE branches (R49 wave 3).

The zip connector's list/extract/unknown paths, the webfetch offline and
charset branches, and the vocab lens's degradation paths — a connector that
fails clean on unknown input is the contract; a lens that degrades honestly
is the law.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from universal_mind.zip_suite import ZipSuite


class TestZipLivePaths:
    def test_pack_with_a_missing_path_reports_honestly(self, tmp_path: Path) -> None:
        result = ZipSuite().pack(["missing-file.txt"])
        assert result["ok"] is False
        assert "missing-file.txt" in result.get("missing", [])

    def test_list_contents_on_a_non_zip_reports_honestly(self, tmp_path: Path) -> None:
        p = tmp_path / "not.zip"
        p.write_bytes(b"plain text, not a zip")
        result = ZipSuite().list_contents(str(p))
        assert result["ok"] is False

    def test_list_contents_on_a_missing_file(self, tmp_path: Path) -> None:
        result = ZipSuite().list_contents(str(tmp_path / "nope.zip"))
        assert result["ok"] is False
        assert "file not found" in result["error"]

    def test_extract_on_a_missing_file(self, tmp_path: Path) -> None:
        result = ZipSuite().extract(str(tmp_path / "nope.zip"), str(tmp_path))
        assert result["ok"] is False
        assert "file not found" in result["error"]

    def test_a_real_zip_round_trips(self, tmp_path: Path) -> None:
        src = tmp_path / "doc.txt"
        src.write_text("محتوا", encoding="utf-8")
        suite = ZipSuite()
        packed = suite.pack([str(src)], str(tmp_path))
        assert packed["ok"] is True
        listed = suite.list_contents(packed["path"])
        assert listed["ok"] is True
        extracted = suite.extract(packed["path"], str(tmp_path / "unpacked"))
        assert extracted["ok"] is True
        assert (tmp_path / "unpacked" / "doc.txt").read_text(encoding="utf-8") == "محتوا"

    def test_the_connector_list_and_unknown_paths(self, tmp_path: Path) -> None:
        from universal_mind.zip_suite import ZipSuiteConnector

        src = tmp_path / "doc.txt"
        src.write_text("محتوا", encoding="utf-8")
        suite = ZipSuite()
        packed = suite.pack([str(src)], str(tmp_path))
        connector = ZipSuiteConnector()
        r1 = connector.connect({}, {"operation": "list", "path": packed["path"]})
        assert r1.ok is True
        r2 = connector.connect({}, {"operation": "extract", "path": packed["path"]})
        assert r2.ok is True
        r3 = connector.connect({}, {"operation": "quantum"})
        assert r3.ok is False  # unknown fails clean

    def test_the_connector_without_a_zip_reports_clean(self, tmp_path: Path) -> None:
        from universal_mind.zip_suite import ZipSuiteConnector

        connector = ZipSuiteConnector()
        r = connector.connect({}, {"operation": "list", "path": str(tmp_path / "no.zip")})
        assert r.ok is False


class TestWebfetchOffline:
    def test_an_offline_fetch_names_the_reason(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        result = WebFetchTool().fetch("http://127.0.0.1:1/no-such-host")  # port 1 = refused
        assert result["ok"] is False
        assert "error" in result

    def test_an_oversized_body_is_truncated(self) -> None:
        # _MAX_BYTES truncation — a real body larger than the cap
        from unittest.mock import patch as mp

        from universal_mind import webfetch_tool as wf
        from universal_mind.webfetch_tool import WebFetchTool

        big = b"x" * (wf._MAX_BYTES + 5000)

        import email.message as _em

        msg = _em.Message()
        msg["Content-Type"] = "text/plain; charset=utf-8"

        class FakeResponse:
            status = 200
            headers = msg

            def read(self, n: int = -1) -> bytes:
                return big

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *a: object) -> None:
                pass

        tool = WebFetchTool()
        with mp("urllib.request.urlopen", return_value=FakeResponse()):
            result = tool.fetch("http://example.com/big")
        assert result["ok"] is True
        assert result["truncated"] is True  # the cap bit
        assert result["chars"] <= wf._MAX_BYTES  # truncated, not OOM


class TestVocabLenses:
    def test_identical_words_have_zero_distance(self) -> None:
        from universal_mind.vocab_breathing import _levenshtein

        assert _levenshtein("نمودار", "نمودار") == 0

    def test_an_empty_second_word_distances_the_first(self) -> None:
        from universal_mind.vocab_breathing import _levenshtein

        assert _levenshtein("نمودار", "") == 6

    def test_the_nearest_capability_names_its_distance(self) -> None:
        """The lens returns the closest word + its HONEST distance — a far
        match is named with the number, never hidden (the caller's gate
        decides what distance is acceptable)."""
        from universal_mind.vocab_breathing import _nearest_capability

        hit = _nearest_capability("zzzzzzzzzzzz")
        assert hit is not None
        word, dist = hit
        assert isinstance(dist, int) and dist > 0  # the honest distance, named

    def test_a_nearest_capability_finds_a_typo(self) -> None:
        from universal_mind.vocab_breathing import _nearest_capability

        hit = _nearest_capability("نمودا")
        assert hit is not None
        assert hit[0]  # a real capability word

    def test_a_degraded_vocab_lens_stays_honest(self) -> None:
        """A broken store: suggestions=[] — the lens is a view, never fatal."""

        from universal_mind import vocab_breathing as vb

        class BrokenSuite:
            def query(self, sql: str, params: Any = None) -> dict[str, Any]:
                raise RuntimeError("نبود")

        assert vb.suggestions(db=BrokenSuite()) == []  # type: ignore[arg-type]


__test__ = True
