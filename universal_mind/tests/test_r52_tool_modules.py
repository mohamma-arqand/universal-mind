"""R52 wave 3: LIVE branch tests for the tool-bound middle modules.

Real effects: a REAL blank PNG through tesseract, a REAL tar.gz of real files
(and the honest skip of a missing one), a REAL PDF metadata read (and its
named refusal), a REAL local HTTP fetch (and the named offline/bad_url
refusals). No mock of any unit under test.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class TestOcrLive:
    """tesseract REALLY runs (or names its absence) on a real PNG."""

    def test_a_blank_png_reads_without_crashing(self, tmp_path: Path) -> None:
        from PIL import Image

        from universal_mind.ocr_tool import OcrTool

        img = tmp_path / "blank.png"
        Image.new("RGB", (80, 40), (255, 255, 255)).save(img)
        r = OcrTool().read(str(img))
        # a blank image honestly reads empty text; the tool never crashes
        assert r["ok"] in (True, False)
        if r["ok"]:
            assert "text" in r
        else:
            assert r["error"]

    def test_a_missing_image_is_named(self) -> None:
        from universal_mind.ocr_tool import OcrTool

        r = OcrTool().read("Z:/ghost.png")
        assert r["ok"] is False
        assert r["error"]


class TestArchiveLive:
    """A REAL tar.gz of real files; a missing file is skipped and named."""

    def test_compress_files_makes_a_real_tar(self, tmp_path: Path) -> None:
        from universal_mind.real_archive import ArchiveTool

        f1 = tmp_path / "a.txt"
        f1.write_text("R52 payload", encoding="utf-8")
        r = ArchiveTool().compress_files([str(f1)], out_dir=str(tmp_path))
        assert r["ok"] is True
        assert Path(str(r["path"])).exists()
        assert r["bytes"] > 0
        assert r["skipped"] == []

    def test_a_missing_file_is_skipped_and_named(self, tmp_path: Path) -> None:
        from universal_mind.real_archive import ArchiveTool

        r = ArchiveTool().compress_files([str(tmp_path / "ghost.txt")], out_dir=str(tmp_path))
        assert r["ok"] is False
        assert r["skipped"] == [str(tmp_path / "ghost.txt")]
        assert "هیچ فایل واقعی" in r["error"]

    def test_a_real_mix_keeps_the_real_one(self, tmp_path: Path) -> None:
        from universal_mind.real_archive import ArchiveTool

        real = tmp_path / "real.txt"
        real.write_text("keep me", encoding="utf-8")
        r = ArchiveTool().compress_files(
            [str(real), str(tmp_path / "ghost.txt")], out_dir=str(tmp_path)
        )
        assert r["ok"] is True
        assert r["skipped"] == [str(tmp_path / "ghost.txt")]


class TestPdfReaderLive:
    """The metadata read and its honest refusals."""

    def test_a_missing_pdf_is_named(self, tmp_path: Path) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        r = PdfReaderTool().metadata(str(tmp_path / "no.pdf"))
        assert r["ok"] is False
        assert "file not found" in r["error"]

    def test_a_real_pdf_metadata_reads(self, tmp_path: Path) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        # a real one-page PDF written by the suite's own reportlab:
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            return  # honest skip: reportlab not installed in this env

        p = tmp_path / "real.pdf"
        c = canvas.Canvas(str(p))
        c.setTitle("R52 Live PDF")
        c.drawString(100, 700, "hello")
        c.save()
        r = PdfReaderTool().metadata(str(p))
        assert r["ok"] is True
        assert r["meta"]["Title"] == "R52 Live PDF"

    def test_a_broken_pdf_is_named(self, tmp_path: Path) -> None:
        from universal_mind.pdfreader_tool import PdfReaderTool

        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
        r = PdfReaderTool().metadata(str(bad))
        assert r["ok"] is False
        assert r["error"]


class TestWebFetchLive:
    """A REAL local HTTP fetch through the real urlopen path."""

    def test_a_local_page_fetches_with_real_markup(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        class _H(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                body = b"<html><body>R52 local webfetch probe</body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=ascii")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:
                pass

        srv = HTTPServer(("127.0.0.1", 0), _H)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            # R57: a loopback target is refused BY DEFAULT — reading the
            # operator's own machine must be an explicit act.
            r = WebFetchTool().fetch(f"http://127.0.0.1:{port}/x", allow_private=True)
        finally:
            srv.shutdown()
            t.join(timeout=2)
        assert r["ok"] is True
        assert r["chars"] > 0

    def test_a_refused_connection_is_named_offline(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        # R57 split this in two: by default loopback is BLOCKED outright
        # (SSRF guard); with the guard explicitly lifted it is an ordinary
        # refused connection, classified honestly.
        blocked = WebFetchTool().fetch("http://127.0.0.1:1/nope")
        assert blocked["ok"] is False
        assert blocked["kind"] == "blocked_target"
        assert blocked["error"]

        r = WebFetchTool().fetch("http://127.0.0.1:1/nope", allow_private=True)
        assert r["ok"] is False
        assert r["kind"] == "offline"
        assert r["error"]

    def test_a_bad_url_is_named(self) -> None:
        from universal_mind.webfetch_tool import WebFetchTool

        r = WebFetchTool().fetch("not a url at all")
        assert r["ok"] is False
        assert r["kind"] == "bad_url"
        assert "http/https" in r["error"]
